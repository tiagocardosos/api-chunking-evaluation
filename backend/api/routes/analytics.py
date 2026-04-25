from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from statistics import mean, median, stdev
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends
from scipy.stats import wilcoxon as scipy_wilcoxon
from sqlalchemy.orm import Session

from core.database import get_db
from models.db import Experiment, ExperimentResult
from models.enums import ExperimentStatus
from models.schemas import (
    BoxPlotStats,
    DistributionsResponse,
    MetricStats,
    RankingsResponse,
    StatTestResult,
    StatTestsResponse,
    StrategiesResponse,
    StrategyMetrics,
    StrategyRanking,
    TemporalExperiment,
    TemporalResponse,
)

router = APIRouter()

METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
    "mrr",
]


@router.get("/strategies", response_model=StrategiesResponse)
def get_strategy_analytics(db: Session = Depends(get_db)):
    """Médias, medianas e desvio padrão de cada métrica RAGAS por estratégia."""
    rows = _load_completed_results(db)

    strategy_results: dict[str, list[ExperimentResult]] = defaultdict(list)
    strategy_experiments: dict[str, set[str]] = defaultdict(set)

    for exp, result in rows:
        strategy_results[exp.chunking_strategy].append(result)
        strategy_experiments[exp.chunking_strategy].add(exp.id)

    strategies = []
    for strategy, results in sorted(strategy_results.items()):
        metric_stats = {
            metric: _compute_stats(
                [getattr(r, metric) for r in results if getattr(r, metric) is not None]
            )
            for metric in METRICS
        }
        strategies.append(
            StrategyMetrics(
                strategy=strategy,
                experiment_count=len(strategy_experiments[strategy]),
                result_count=len(results),
                **metric_stats,
            )
        )

    return StrategiesResponse(strategies=strategies)


@router.get("/distributions", response_model=DistributionsResponse)
def get_distributions(db: Session = Depends(get_db)):
    """Dados de box plot (min, Q1, mediana, Q3, max, outliers) por métrica × estratégia."""
    rows = _load_completed_results(db)

    data: dict[str, dict[str, list[float]]] = {
        metric: defaultdict(list) for metric in METRICS
    }

    for exp, result in rows:
        for metric in METRICS:
            value = getattr(result, metric)
            if value is not None:
                data[metric][exp.chunking_strategy].append(value)

    return DistributionsResponse(
        metrics={
            metric: {
                strategy: _compute_boxplot(values)
                for strategy, values in strategies.items()
            }
            for metric, strategies in data.items()
        }
    )


@router.get("/statistical-tests", response_model=StatTestsResponse)
def get_statistical_tests(db: Session = Depends(get_db)):
    """Wilcoxon signed-rank pareado + correção Holm-Bonferroni entre todos os pares de estratégias."""
    rows = _load_completed_results(db)

    # Agrega por estratégia → pergunta → métrica (média quando há múltiplos experimentos)
    raw: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for exp, result in rows:
        for metric in METRICS:
            value = getattr(result, metric)
            if value is not None:
                raw[exp.chunking_strategy][result.question][metric].append(value)

    aggregated: dict[str, dict[str, dict[str, float]]] = {
        strategy: {
            question: {
                metric: mean(values)
                for metric, values in metrics.items()
                if values
            }
            for question, metrics in questions.items()
        }
        for strategy, questions in raw.items()
    }

    strategies = sorted(aggregated.keys())
    all_comparisons: list[StatTestResult] = []

    for metric in METRICS:
        metric_comparisons: list[StatTestResult] = []

        for strat_a, strat_b in combinations(strategies, 2):
            questions_a = aggregated.get(strat_a, {})
            questions_b = aggregated.get(strat_b, {})
            common = set(questions_a) & set(questions_b)

            pairs: list[tuple[float, float]] = [
                (questions_a[q][metric], questions_b[q][metric])
                for q in common
                if metric in questions_a[q] and metric in questions_b[q]
            ]

            if len(pairs) < 10:
                continue

            arr_a = np.array([p[0] for p in pairs])
            arr_b = np.array([p[1] for p in pairs])
            n = len(pairs)

            if np.all(arr_a == arr_b):
                metric_comparisons.append(
                    StatTestResult(
                        strategy_a=strat_a, strategy_b=strat_b, metric=metric,
                        n_pairs=n,
                        median_a=float(np.median(arr_a)), median_b=float(np.median(arr_b)),
                        statistic=0.0, p_value=1.0, p_corrected=1.0,
                        effect_size_r=0.0, significant=False, winner=None,
                    )
                )
                continue

            stat, pvalue = scipy_wilcoxon(arr_a, arr_b, alternative="two-sided", zero_method="wilcox")
            effect_r = float(np.clip(1.0 - (2.0 * stat) / (n * (n + 1) / 2), -1.0, 1.0))

            metric_comparisons.append(
                StatTestResult(
                    strategy_a=strat_a, strategy_b=strat_b, metric=metric,
                    n_pairs=n,
                    median_a=round(float(np.median(arr_a)), 4),
                    median_b=round(float(np.median(arr_b)), 4),
                    statistic=round(float(stat), 4),
                    p_value=round(float(pvalue), 4),
                    p_corrected=round(float(pvalue), 4),  # substituído abaixo
                    effect_size_r=round(effect_r, 4),
                    significant=False,
                    winner=None,
                )
            )

        all_comparisons.extend(_apply_holm_bonferroni(metric_comparisons))

    return StatTestsResponse(comparisons=all_comparisons)


@router.get("/rankings", response_model=RankingsResponse)
def get_rankings(db: Session = Depends(get_db)):
    """Ranking de estratégias por vitórias (melhor média) em cada métrica."""
    rows = _load_completed_results(db)

    data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for exp, result in rows:
        for metric in METRICS:
            value = getattr(result, metric)
            if value is not None:
                data[exp.chunking_strategy][metric].append(value)

    if not data:
        return RankingsResponse(rankings=[], metric_leaders={})

    strategy_means: dict[str, dict[str, float]] = {
        strategy: {
            metric: mean(values)
            for metric, values in metrics.items()
            if values
        }
        for strategy, metrics in data.items()
    }

    metric_leaders: dict[str, str] = {}
    wins: dict[str, list[str]] = defaultdict(list)

    for metric in METRICS:
        best = max(
            ((s, m[metric]) for s, m in strategy_means.items() if metric in m),
            key=lambda x: x[1],
            default=None,
        )
        if best:
            metric_leaders[metric] = best[0]
            wins[best[0]].append(metric)

    rankings = sorted(
        [
            StrategyRanking(
                strategy=strategy,
                wins=len(wins.get(strategy, [])),
                metrics_won=wins.get(strategy, []),
                score=round(mean(list(means.values())), 4) if means else 0.0,
            )
            for strategy, means in strategy_means.items()
        ],
        key=lambda x: (-x.wins, -x.score),
    )

    return RankingsResponse(rankings=rankings, metric_leaders=metric_leaders)


@router.get("/temporal", response_model=TemporalResponse)
def get_temporal(db: Session = Depends(get_db)):
    """Série temporal de experimentos concluídos com métricas médias por experimento."""
    experiments = (
        db.query(Experiment)
        .filter(Experiment.status == ExperimentStatus.completed.value)
        .order_by(Experiment.created_at.asc())
        .all()
    )

    result = []
    for exp in experiments:
        exp_results = (
            db.query(ExperimentResult)
            .filter(ExperimentResult.experiment_id == exp.id)
            .all()
        )
        result.append(
            TemporalExperiment(
                id=exp.id,
                name=exp.name,
                strategy=exp.chunking_strategy,
                created_at=exp.created_at,
                completed_at=exp.completed_at,
                result_count=len(exp_results),
                avg_faithfulness=_avg(r.faithfulness for r in exp_results),
                avg_answer_relevancy=_avg(r.answer_relevancy for r in exp_results),
                avg_context_precision=_avg(r.context_precision for r in exp_results),
                avg_context_recall=_avg(r.context_recall for r in exp_results),
                avg_answer_correctness=_avg(r.answer_correctness for r in exp_results),
                avg_mrr=_avg(r.mrr for r in exp_results),
            )
        )

    return TemporalResponse(experiments=result)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_completed_results(db: Session) -> list[tuple[Experiment, ExperimentResult]]:
    return (
        db.query(Experiment, ExperimentResult)
        .join(ExperimentResult, ExperimentResult.experiment_id == Experiment.id)
        .filter(Experiment.status == ExperimentStatus.completed.value)
        .all()
    )


def _compute_stats(values: list[float]) -> MetricStats:
    if not values:
        return MetricStats(mean=None, median=None, std=None)
    return MetricStats(
        mean=round(mean(values), 4),
        median=round(median(values), 4),
        std=round(stdev(values), 4) if len(values) > 1 else 0.0,
    )


def _compute_boxplot(values: list[float]) -> BoxPlotStats:
    arr = np.array(sorted(values), dtype=float)
    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return BoxPlotStats(
        min=float(arr.min()),
        q1=q1,
        median=float(np.median(arr)),
        q3=q3,
        max=float(arr.max()),
        outliers=[round(float(v), 4) for v in arr if v < lower or v > upper],
        n=len(values),
    )


def _avg(values) -> Optional[float]:
    valid = [v for v in values if v is not None]
    return round(mean(valid), 4) if valid else None


def _apply_holm_bonferroni(comparisons: list[StatTestResult]) -> list[StatTestResult]:
    if not comparisons:
        return []
    m = len(comparisons)
    sorted_comps = sorted(comparisons, key=lambda x: x.p_value)
    result = []
    for k, cr in enumerate(sorted_comps, start=1):
        p_corrected = round(min(cr.p_value * (m - k + 1), 1.0), 4)
        significant = p_corrected < 0.05
        winner = None
        if significant:
            winner = cr.strategy_a if cr.median_a > cr.median_b else cr.strategy_b
        result.append(
            StatTestResult(
                strategy_a=cr.strategy_a, strategy_b=cr.strategy_b, metric=cr.metric,
                n_pairs=cr.n_pairs,
                median_a=cr.median_a, median_b=cr.median_b,
                statistic=cr.statistic,
                p_value=cr.p_value,
                p_corrected=p_corrected,
                effect_size_r=cr.effect_size_r,
                significant=significant,
                winner=winner,
            )
        )
    return result
