"""
Wilcoxon Signed-Rank Test
=========================
Comparações pareadas entre estratégias de chunking para cada métrica.

Por que Wilcoxon (EXPERIMENT-SPEC §7):
    - Distribuições de métricas RAG não são normais → teste não-paramétrico.
    - As 180 perguntas são as MESMAS para todos os experimentos → dados pareados.
    - Wilcoxon signed-rank é mais poderoso que Mann-Whitney para dados pareados.

Múltiplas comparações:
    - 5 estratégias → C(5,2) = 10 pares por métrica.
    - Correção Holm-Bonferroni (controla FWER, mais poderosa que Bonferroni simples).

Tamanho de efeito:
    - Rank-biserial correlation r = 1 − (2W) / (n*(n+1)/2)
      Interpretação: |r| < 0.1 trivial, 0.1–0.3 pequeno, 0.3–0.5 médio, > 0.5 grande.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from results_loader import METRIC_COLS


@dataclass
class ComparisonResult:
    strategy_a: str
    strategy_b: str
    metric: str
    n_pairs: int               # nº de perguntas com scores válidos nos dois lados
    median_a: float
    median_b: float
    statistic: float           # estatística W do Wilcoxon
    pvalue: float
    pvalue_corrected: float    # após correção Holm-Bonferroni
    effect_size_r: float       # rank-biserial correlation
    significant: bool          # pvalue_corrected < alpha
    alpha: float = 0.05

    @property
    def winner(self) -> str | None:
        """Retorna o nome da estratégia melhor (ou None se empate)."""
        if not self.significant:
            return None
        return self.strategy_a if self.median_a > self.median_b else self.strategy_b

    def __repr__(self) -> str:
        sig = "✓" if self.significant else "✗"
        return (
            f"{self.strategy_a} vs {self.strategy_b} | {self.metric} | "
            f"p={self.pvalue_corrected:.4f} {sig} | r={self.effect_size_r:.3f} | "
            f"winner={self.winner or 'n/a'}"
        )


def run_all_comparisons(
    results: dict[str, pd.DataFrame],
    alpha: float = 0.05,
    min_pairs: int = 10,
) -> list[ComparisonResult]:
    """
    Executa comparações Wilcoxon para todos os pares de estratégias × métricas.

    Args:
        results  : dict strategy → DataFrame (índice = pergunta, colunas = métricas).
        alpha    : nível de significância (após correção).
        min_pairs: mínimo de pares válidos para rodar o teste.

    Returns:
        Lista de ComparisonResult com p-values corrigidos.
    """
    strategies = sorted(results.keys())
    pairs = list(combinations(strategies, 2))
    all_results: list[ComparisonResult] = []

    for metric in METRIC_COLS:
        metric_results: list[tuple[float, ComparisonResult]] = []

        for strat_a, strat_b in pairs:
            cr = _compare_pair(
                strategy_a=strat_a,
                strategy_b=strat_b,
                df_a=results[strat_a],
                df_b=results[strat_b],
                metric=metric,
                alpha=alpha,
                min_pairs=min_pairs,
            )
            if cr is not None:
                metric_results.append((cr.pvalue, cr))

        # Correção Holm-Bonferroni dentro de cada métrica
        if metric_results:
            corrected = _holm_bonferroni(
                [(pv, cr) for pv, cr in metric_results], alpha=alpha
            )
            all_results.extend(corrected)

    return all_results


def results_to_dataframe(comparisons: list[ComparisonResult]) -> pd.DataFrame:
    """Converte lista de ComparisonResult em DataFrame para análise/exportação."""
    return pd.DataFrame([
        {
            "strategy_a": c.strategy_a,
            "strategy_b": c.strategy_b,
            "metric": c.metric,
            "n_pairs": c.n_pairs,
            "median_a": round(c.median_a, 4),
            "median_b": round(c.median_b, 4),
            "p_value": round(c.pvalue, 4),
            "p_corrected": round(c.pvalue_corrected, 4),
            "effect_size_r": round(c.effect_size_r, 3),
            "significant": c.significant,
            "winner": c.winner or "—",
        }
        for c in comparisons
    ])


def pvalue_matrix(
    comparisons: list[ComparisonResult],
    metric: str,
) -> pd.DataFrame:
    """
    Gera matriz simétrica de p-values corrigidos para uma métrica específica.
    Útil para tabelas do artigo.

        Linhas/Colunas: estratégias
        Células: p-value corrigido (NaN na diagonal e pares não calculados)
    """
    strategies = sorted({c.strategy_a for c in comparisons} | {c.strategy_b for c in comparisons})
    mat = pd.DataFrame(np.nan, index=strategies, columns=strategies)

    for c in comparisons:
        if c.metric != metric:
            continue
        mat.loc[c.strategy_a, c.strategy_b] = c.pvalue_corrected
        mat.loc[c.strategy_b, c.strategy_a] = c.pvalue_corrected

    # Diagonal = 1.0 (comparação consigo mesmo)
    for s in strategies:
        mat.loc[s, s] = 1.0

    return mat


# ── Internals ─────────────────────────────────────────────────────────────────

def _compare_pair(
    strategy_a: str,
    strategy_b: str,
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    metric: str,
    alpha: float,
    min_pairs: int,
) -> Optional[ComparisonResult]:
    if metric not in df_a.columns or metric not in df_b.columns:
        return None

    # Alinha por índice (pergunta) e descarta NaNs
    combined = pd.concat(
        [df_a[metric].rename("a"), df_b[metric].rename("b")],
        axis=1,
        join="inner",
    ).dropna()

    n = len(combined)
    if n < min_pairs:
        return None

    scores_a = combined["a"].values
    scores_b = combined["b"].values

    # Descarta empates exatos (Wilcoxon os ignora de qualquer forma)
    diff = scores_a - scores_b
    if np.all(diff == 0):
        # Idênticos → sem diferença, p=1.0
        return ComparisonResult(
            strategy_a=strategy_a, strategy_b=strategy_b, metric=metric,
            n_pairs=n, median_a=float(np.median(scores_a)), median_b=float(np.median(scores_b)),
            statistic=0.0, pvalue=1.0, pvalue_corrected=1.0,
            effect_size_r=0.0, significant=False, alpha=alpha,
        )

    stat, pvalue = wilcoxon(scores_a, scores_b, alternative="two-sided", zero_method="wilcox")

    # Rank-biserial correlation: r = 1 - 2W / (n*(n+1)/2)
    # W aqui é a soma dos ranks menores (scipy retorna min(W+, W-))
    n_total_rank = n * (n + 1) / 2
    effect_r = 1.0 - (2.0 * stat) / n_total_rank
    # Garante que está no intervalo [-1, 1]
    effect_r = float(np.clip(effect_r, -1.0, 1.0))

    return ComparisonResult(
        strategy_a=strategy_a,
        strategy_b=strategy_b,
        metric=metric,
        n_pairs=n,
        median_a=float(np.median(scores_a)),
        median_b=float(np.median(scores_b)),
        statistic=float(stat),
        pvalue=float(pvalue),
        pvalue_corrected=float(pvalue),  # será substituído após correção
        effect_size_r=effect_r,
        significant=float(pvalue) < alpha,
        alpha=alpha,
    )


def _holm_bonferroni(
    pvalue_result_pairs: list[tuple[float, ComparisonResult]],
    alpha: float,
) -> list[ComparisonResult]:
    """
    Aplica correção Holm-Bonferroni nos p-values de um grupo (ex: mesma métrica).

    Algoritmo:
        1. Ordena p-values em ordem crescente.
        2. Para cada k (1-indexed): limiar_k = alpha / (m - k + 1).
        3. Rejeita H0 para todos os testes anteriores ao primeiro não-rejeito.
    """
    if not pvalue_result_pairs:
        return []

    m = len(pvalue_result_pairs)
    sorted_pairs = sorted(pvalue_result_pairs, key=lambda x: x[0])

    corrected: list[ComparisonResult] = []
    reject_all_previous = True  # Holm: uma vez que encontramos não-rejeito, paramos

    for k, (_, cr) in enumerate(sorted_pairs, start=1):
        threshold = alpha / (m - k + 1)
        p_corrected = min(cr.pvalue * (m - k + 1), 1.0)

        # Atualiza o resultado com p-value corrigido
        import dataclasses  # noqa: PLC0415
        cr_corrected = dataclasses.replace(
            cr,
            pvalue_corrected=p_corrected,
            significant=(p_corrected < alpha),
        )
        corrected.append(cr_corrected)

    return corrected
