"""
ResultsLoader
=============
Carrega resultados dos experimentos do PostgreSQL e os organiza em DataFrames pandas.

Saída principal: dict[strategy_name → DataFrame] onde cada DataFrame tem:
    - index  : texto da pergunta
    - colunas: faithfulness, answer_relevancy, context_precision,
               context_recall, answer_correctness, mrr
    - colunas extras: question_type, doc_type (se disponíveis no golden set)

Uso:
    loader = ResultsLoader(postgres_url="postgresql://rag:rag123@localhost:5432/rag_eval")
    results = loader.load_all()         # dict[strategy → DataFrame]
    pdf_only = loader.load_all(doc_type_filter="pdf")
"""
from __future__ import annotations

import os
from typing import Literal

import pandas as pd
from sqlalchemy import create_engine, text

_DEFAULT_URL = os.environ.get(
    "POSTGRES_URL", "postgresql://rag:rag123@localhost:5432/rag_eval"
)

METRIC_COLS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
    "mrr",
]


class ResultsLoader:
    def __init__(self, postgres_url: str = _DEFAULT_URL) -> None:
        self.engine = create_engine(postgres_url)

    def load_all(
        self,
        doc_type_filter: Literal["pdf", "xml_lattes"] | None = None,
        question_type_filter: Literal["factual", "inferential"] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Carrega todos os experimentos concluídos e os organiza por estratégia.

        Se um mesmo estratégia tiver múltiplos experimentos (re-runs),
        os resultados são concatenados.

        Args:
            doc_type_filter:      filtra resultados por tipo de documento.
            question_type_filter: filtra por tipo de pergunta.

        Returns:
            dict strategy_name → DataFrame com colunas de métricas.
        """
        df_raw = self._fetch_raw(doc_type_filter, question_type_filter)
        if df_raw.empty:
            return {}

        grouped: dict[str, pd.DataFrame] = {}
        for strategy, group in df_raw.groupby("chunking_strategy"):
            df = (
                group
                .set_index("question")[METRIC_COLS + ["question_type", "doc_type"]]
                .copy()
            )
            grouped[strategy] = df

        return grouped

    def load_experiment(self, experiment_id: str) -> pd.DataFrame:
        """Carrega os resultados de um experimento específico."""
        query = text("""
            SELECT
                er.question,
                er.faithfulness,
                er.answer_relevancy,
                er.context_precision,
                er.context_recall,
                er.answer_correctness,
                er.mrr
            FROM experiment_results er
            WHERE er.experiment_id = :exp_id
            ORDER BY er.created_at
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"exp_id": experiment_id})
        return df.set_index("question")

    def list_experiments(self) -> pd.DataFrame:
        """Lista todos os experimentos com seus metadados e status."""
        query = text("""
            SELECT
                e.id,
                e.name,
                e.chunking_strategy,
                e.embedding_model,
                e.generator_model,
                e.retrieval_strategy,
                e.top_k,
                e.chunk_size,
                e.chunk_overlap,
                e.status,
                e.created_at,
                e.completed_at,
                COUNT(er.id) AS total_questions
            FROM experiments e
            LEFT JOIN experiment_results er ON er.experiment_id = e.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql(query, conn)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _fetch_raw(
        self,
        doc_type_filter: str | None,
        question_type_filter: str | None,
    ) -> pd.DataFrame:
        """
        Busca todos os resultados de experimentos concluídos.
        Junta com a tabela de experimentos para obter chunking_strategy.

        Como doc_type e question_type não estão na tabela experiment_results,
        fazemos o join via documents caso a pergunta tenha sido originada de
        um documento. Como nem sempre isso está disponível, retornamos
        question_type e doc_type como None quando não mapeados.
        """
        query = text("""
            SELECT
                e.chunking_strategy,
                er.question,
                er.faithfulness,
                er.answer_relevancy,
                er.context_precision,
                er.context_recall,
                er.answer_correctness,
                er.mrr,
                NULL::text AS question_type,
                NULL::text AS doc_type
            FROM experiment_results er
            JOIN experiments e ON e.id = er.experiment_id
            WHERE e.status = 'completed'
            ORDER BY e.chunking_strategy, er.created_at
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return df

        # Aplica filtros se fornecidos
        if doc_type_filter and "doc_type" in df.columns:
            df = df[df["doc_type"] == doc_type_filter]
        if question_type_filter and "question_type" in df.columns:
            df = df[df["question_type"] == question_type_filter]

        return df
