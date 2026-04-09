"""
Evaluator
=========
Wrapper sobre RAGAS para calcular as 5 métricas do experimento.

Métricas (EXPERIMENT-SPEC §2):
    - Faithfulness          : resposta está ancorada no contexto? (LLM-based)
    - Answer Relevancy      : resposta é relevante para a pergunta? (embedding-based)
    - Context Precision     : chunks recuperados são precisos? (LLM-based)
    - Context Recall        : contexto cobre a ground truth? (LLM-based, requer ground_truth)
    - Answer Correctness    : resposta está correta vs ground_truth? (LLM-based + embedding)

Métricas customizadas:
    - MRR (Mean Reciprocal Rank): inverso da posição do primeiro chunk "relevante".
      Relevância: chunk que contém algum trecho da expected_answer (proxy heurístico,
      pois não temos anotações chunk-level).

Nota sobre ragas>=0.1:
    RAGAS usa LLMs para avaliar Faithfulness e Context Precision/Recall.
    Configuramos o mesmo GPT-4o-mini e text-embedding-3-small do experimento
    para manter consistência e controle de custos.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Estrutura de resultado por pergunta
PerQuestionScore = dict[str, float | None]


def evaluate_with_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str | None],
    llm_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
) -> list[PerQuestionScore]:
    """
    Executa avaliação RAGAS em batch sobre todos os pares pergunta/resposta.

    Args:
        questions     : perguntas do golden set.
        answers       : respostas geradas pelo RAG.
        contexts      : lista de listas com o conteúdo dos chunks recuperados.
        ground_truths : respostas esperadas (None para perguntas sem gabarito).
        llm_model     : modelo OpenAI para métricas LLM-based.
        embedding_model: modelo OpenAI para métricas embedding-based.

    Returns:
        Lista de dicts com as métricas por pergunta (None se métrica não aplicável).
    """
    try:
        return _run_ragas(
            questions, answers, contexts, ground_truths, llm_model, embedding_model
        )
    except Exception as exc:
        logger.error("RAGAS evaluation falhou: %s — retornando scores None.", exc)
        return [_empty_score() for _ in questions]


def compute_mrr(
    contexts: list[list[str]],
    ground_truths: list[str | None],
) -> list[float | None]:
    """
    Calcula MRR por pergunta usando a heurística de conteúdo.

    Para cada pergunta:
        1. Procura a posição (1-indexed) do primeiro chunk que contém
           algum fragmento da ground truth (≥5 tokens consecutivos).
        2. MRR_i = 1 / posição  (0.0 se nenhum chunk contiver a resposta).
        3. Retorna None se a pergunta não tiver ground_truth.
    """
    results: list[float | None] = []

    for chunks, gt in zip(contexts, ground_truths):
        if not gt:
            results.append(None)
            continue

        gt_lower = gt.lower()
        # Tokens da ground truth para matching parcial
        gt_tokens = gt_lower.split()
        # Janelas de 5 tokens consecutivos da ground truth
        windows = [
            " ".join(gt_tokens[i : i + 5])
            for i in range(max(1, len(gt_tokens) - 4))
        ]

        rr = 0.0
        for rank, chunk in enumerate(chunks, start=1):
            chunk_lower = chunk.lower()
            if any(w in chunk_lower for w in windows):
                rr = 1.0 / rank
                break

        results.append(rr)

    return results


def compute_recall_at_k(
    contexts: list[list[str]],
    ground_truths: list[str | None],
    k: int = 5,
) -> list[float | None]:
    """
    Recall@k: 1.0 se qualquer um dos top-k chunks contém a ground truth, 0.0 caso contrário.
    Retorna None se não houver ground_truth.
    """
    results: list[float | None] = []

    for chunks, gt in zip(contexts, ground_truths):
        if not gt:
            results.append(None)
            continue

        top_k_chunks = chunks[:k]
        gt_lower = gt.lower()
        gt_tokens = gt_lower.split()
        windows = [
            " ".join(gt_tokens[i : i + 5])
            for i in range(max(1, len(gt_tokens) - 4))
        ]

        hit = any(
            any(w in chunk.lower() for w in windows)
            for chunk in top_k_chunks
        )
        results.append(1.0 if hit else 0.0)

    return results


# ── Internals ─────────────────────────────────────────────────────────────────

def _run_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str | None],
    llm_model: str,
    embedding_model: str,
) -> list[PerQuestionScore]:
    from datasets import Dataset  # noqa: PLC0415
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: PLC0415
    from ragas import evaluate  # noqa: PLC0415
    from ragas.metrics import (  # noqa: PLC0415
        answer_correctness,
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    from core.config import settings  # noqa: PLC0415

    # Substitui None por string vazia (RAGAS não aceita None no Dataset)
    safe_ground_truths = [gt or "" for gt in ground_truths]
    has_ground_truth = any(gt for gt in ground_truths)

    data: dict[str, Any] = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": safe_ground_truths,
    }

    dataset = Dataset.from_dict(data)

    # Métricas que não precisam de ground_truth
    metrics = [faithfulness, answer_relevancy, context_precision]
    if has_ground_truth:
        metrics += [context_recall, answer_correctness]

    llm = ChatOpenAI(
        model=llm_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        api_key=settings.openai_api_key,
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,  # não aborta em falhas pontuais
    )

    df = result.to_pandas()

    scores: list[PerQuestionScore] = []
    for _, row in df.iterrows():
        scores.append({
            "faithfulness": _safe_float(row.get("faithfulness")),
            "answer_relevancy": _safe_float(row.get("answer_relevancy")),
            "context_precision": _safe_float(row.get("context_precision")),
            "context_recall": _safe_float(row.get("context_recall")) if has_ground_truth else None,
            "answer_correctness": _safe_float(row.get("answer_correctness")) if has_ground_truth else None,
        })

    return scores


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


def _empty_score() -> PerQuestionScore:
    return {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "context_recall": None,
        "answer_correctness": None,
    }
