"""
Tables
======
Gera tabelas comparativas em múltiplos formatos (CSV, Markdown, LaTeX) para o artigo.

Tabelas produzidas:
    1. summary_table    : Mediana ± IQR de cada métrica por estratégia.
    2. pvalue_table     : Matriz de p-values corrigidos (Holm-Bonferroni) por métrica.
    3. ranking_table    : Ranking de estratégias por métrica (quem venceu mais comparações).
    4. breakdown_table  : Métricas separadas por tipo de documento (PDF vs XML Lattes)
                          e tipo de pergunta (factual vs inferencial).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from results_loader import METRIC_COLS
from wilcoxon import ComparisonResult, pvalue_matrix

# Nomes legíveis para o artigo
_METRIC_LABELS = {
    "faithfulness":        "Faithfulness",
    "answer_relevancy":    "Answer Relevancy",
    "context_precision":   "Context Precision",
    "context_recall":      "Context Recall",
    "answer_correctness":  "Answer Correctness",
    "mrr":                 "MRR",
}

_STRATEGY_LABELS = {
    "fixed_size":       "Fixed-Size",
    "recursive":        "Recursive",
    "sentence":         "Sentence",
    "semantic":         "Semantic",
    "structure_aware":  "Structure-Aware",
}


def summary_table(
    results: dict[str, pd.DataFrame],
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    """
    Tabela principal: Mediana (IQR) de cada métrica × estratégia.

    Formato: linhas = estratégias, colunas = métricas.
    Células: "0.732 (0.156)" → mediana (IQR = Q3 - Q1).
    """
    metrics = metrics or METRIC_COLS
    rows = []

    for strategy in sorted(results.keys()):
        df = results[strategy]
        row = {"Estratégia": _STRATEGY_LABELS.get(strategy, strategy)}

        for metric in metrics:
            if metric not in df.columns:
                row[_METRIC_LABELS.get(metric, metric)] = "—"
                continue

            values = df[metric].dropna()
            if values.empty:
                row[_METRIC_LABELS.get(metric, metric)] = "—"
                continue

            median = values.median()
            iqr = values.quantile(0.75) - values.quantile(0.25)
            row[_METRIC_LABELS.get(metric, metric)] = f"{median:.3f} ({iqr:.3f})"

        rows.append(row)

    return pd.DataFrame(rows).set_index("Estratégia")


def pvalue_table(
    comparisons: list[ComparisonResult],
    metric: str,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Matriz de p-values corrigidos para uma métrica específica.

    Células: p-value. Células com * = p < alpha (diferença significativa).
    Diagonal: "—".
    """
    mat = pvalue_matrix(comparisons, metric)

    # Formata células: adiciona * para significativo
    formatted = pd.DataFrame(index=mat.index, columns=mat.columns, dtype=object)
    for row in mat.index:
        for col in mat.columns:
            val = mat.loc[row, col]
            if row == col:
                formatted.loc[row, col] = "—"
            elif np.isnan(val):
                formatted.loc[row, col] = "n/d"
            elif val < alpha:
                formatted.loc[row, col] = f"{val:.4f}*"
            else:
                formatted.loc[row, col] = f"{val:.4f}"

    # Rename índices para labels legíveis
    formatted.index = [_STRATEGY_LABELS.get(s, s) for s in mat.index]
    formatted.columns = [_STRATEGY_LABELS.get(s, s) for s in mat.columns]
    return formatted


def ranking_table(
    comparisons: list[ComparisonResult],
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Conta vitórias significativas por estratégia × métrica.

    Uma "vitória" = a estratégia teve mediana superior em uma comparação
    significativa (p_corrected < alpha).
    """
    strategies = sorted(
        {c.strategy_a for c in comparisons} | {c.strategy_b for c in comparisons}
    )
    metrics = sorted({c.metric for c in comparisons})

    data: dict[str, dict[str, int]] = {
        _STRATEGY_LABELS.get(s, s): {_METRIC_LABELS.get(m, m): 0 for m in metrics}
        for s in strategies
    }

    for c in comparisons:
        if not c.significant or c.winner is None:
            continue
        s_label = _STRATEGY_LABELS.get(c.winner, c.winner)
        m_label = _METRIC_LABELS.get(c.metric, c.metric)
        data[s_label][m_label] += 1

    df = pd.DataFrame(data).T
    df["Total Vitórias"] = df.sum(axis=1)
    df = df.sort_values("Total Vitórias", ascending=False)
    return df


def breakdown_table(
    results: dict[str, pd.DataFrame],
    split_col: str,         # "doc_type" | "question_type"
    metric: str,
) -> pd.DataFrame:
    """
    Tabela de mediana por estratégia × subgrupo (PDF vs XML ou factual vs inferencial).

    Args:
        split_col: coluna usada para dividir os dados.
        metric:    métrica a analisar.
    """
    rows = []
    for strategy in sorted(results.keys()):
        df = results[strategy]
        if metric not in df.columns or split_col not in df.columns:
            continue

        row = {"Estratégia": _STRATEGY_LABELS.get(strategy, strategy)}
        for group, group_df in df.groupby(split_col):
            values = group_df[metric].dropna()
            row[str(group)] = f"{values.median():.3f}" if not values.empty else "—"

        rows.append(row)

    return pd.DataFrame(rows).set_index("Estratégia")


# ── Exportação ────────────────────────────────────────────────────────────────

def save_all(
    results: dict[str, pd.DataFrame],
    comparisons: list[ComparisonResult],
    output_dir: str | Path = "outputs",
    alpha: float = 0.05,
) -> None:
    """
    Salva todas as tabelas nos formatos CSV, Markdown e LaTeX.

    Cria o diretório de saída se não existir.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Tabela resumo
    summary = summary_table(results)
    _save_table(summary, out / "summary", title="Tabela 1 — Mediana (IQR) por Estratégia")

    # 2. P-values por métrica
    for metric in METRIC_COLS:
        metric_comparisons = [c for c in comparisons if c.metric == metric]
        if not metric_comparisons:
            continue
        pv_table = pvalue_table(metric_comparisons, metric=metric, alpha=alpha)
        label = _METRIC_LABELS.get(metric, metric).lower().replace(" ", "_")
        _save_table(pv_table, out / f"pvalues_{label}", title=f"P-values — {_METRIC_LABELS.get(metric, metric)}")

    # 3. Ranking
    rank = ranking_table(comparisons, alpha=alpha)
    _save_table(rank, out / "ranking", title="Ranking — Vitórias Significativas por Estratégia")

    # 4. Comparações brutas
    comp_df = _comparisons_to_df(comparisons)
    comp_df.to_csv(out / "all_comparisons.csv", index=False)
    print(f"[OK] Comparações brutas: {out / 'all_comparisons.csv'}")

    print(f"\n[OK] Todas as tabelas salvas em: {out.resolve()}")


def _save_table(df: pd.DataFrame, base_path: Path, title: str) -> None:
    # CSV
    df.to_csv(f"{base_path}.csv")

    # Markdown
    md = f"## {title}\n\n"
    md += df.to_markdown()
    Path(f"{base_path}.md").write_text(md, encoding="utf-8")

    # LaTeX
    latex = df.to_latex(
        caption=title,
        label=f"tab:{base_path.name}",
        escape=True,
        bold_rows=True,
    )
    Path(f"{base_path}.tex").write_text(latex, encoding="utf-8")

    print(f"[OK] {title}: {base_path}.{{csv,md,tex}}")


def _comparisons_to_df(comparisons: list[ComparisonResult]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "strategy_a": c.strategy_a,
            "strategy_b": c.strategy_b,
            "metric": c.metric,
            "n_pairs": c.n_pairs,
            "median_a": round(c.median_a, 4),
            "median_b": round(c.median_b, 4),
            "p_value": round(c.pvalue, 6),
            "p_corrected_holm": round(c.pvalue_corrected, 6),
            "effect_size_r": round(c.effect_size_r, 4),
            "significant": c.significant,
            "winner": c.winner or "—",
        }
        for c in comparisons
    ])
