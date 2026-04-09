"""
ExperimentRunner
================
Orquestra um experimento completo:

    Para cada golden question:
        1. Embed da pergunta via OpenAI.
        2. Recupera top_k chunks do Qdrant (semântico ou híbrido).
        3. Gera resposta com GPT-4o-mini (temperature=0, seed=42).

    Ao final do batch:
        4. Avalia todas as respostas com RAGAS em uma única chamada.
        5. Calcula MRR e Recall@5 por pergunta.
        6. Persiste ExperimentResult no PostgreSQL para cada pergunta.
        7. Atualiza status do Experiment para "completed" (ou "failed").

Uso (dentro de um BackgroundTask do FastAPI):
    runner = ExperimentRunner(experiment_id, request, db_factory, vector_store)
    runner.run()
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from core.embeddings import OpenAIEmbedder
from core.evaluator import compute_mrr, compute_recall_at_k, evaluate_with_ragas
from core.vector_store import VectorStore
from models.db import Experiment, ExperimentResult
from models.enums import ExperimentStatus, RetrievalStrategy
from models.schemas import ExperimentRunRequest

logger = logging.getLogger(__name__)


class ExperimentRunner:
    def __init__(
        self,
        experiment_id: str,
        request: ExperimentRunRequest,
        db_factory: Callable[[], Session],
        vector_store: VectorStore,
    ) -> None:
        self.experiment_id = experiment_id
        self.request = request
        self.db_factory = db_factory
        self.vs = vector_store

    def run(self) -> None:
        """
        Executa o experimento completo.
        Captura qualquer exceção e marca o experimento como "failed".
        """
        db = self.db_factory()
        try:
            self._set_status(db, ExperimentStatus.running)
            self._execute(db)
            self._set_status(db, ExperimentStatus.completed)
        except Exception as exc:
            logger.exception("Experimento %s falhou: %s", self.experiment_id, exc)
            self._set_status(db, ExperimentStatus.failed)
        finally:
            db.close()

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _execute(self, db: Session) -> None:
        req = self.request
        embedder = OpenAIEmbedder(model=req.embedding_model)

        questions = [q.question for q in req.golden_questions]
        ground_truths = [q.expected_answer for q in req.golden_questions]

        # ── Fase 1: RAG para cada pergunta ────────────────────────────────────
        logger.info(
            "Experimento %s: processando %d perguntas...",
            self.experiment_id,
            len(questions),
        )

        answers: list[str] = []
        contexts: list[list[str]] = []      # conteúdo dos chunks recuperados
        context_ids: list[list[str]] = []   # chunk_ids para rastreabilidade
        context_scores: list[list[float]] = []

        for i, question in enumerate(questions):
            query_vector = embedder.embed_query(question)

            if req.retrieval_strategy == RetrievalStrategy.hybrid:
                hits = self.vs.search_hybrid(
                    collection_name=req.collection_id,
                    query_vector=query_vector,
                    query_text=question,
                    top_k=req.top_k,
                )
            else:
                hits = self.vs.search_semantic(
                    collection_name=req.collection_id,
                    query_vector=query_vector,
                    top_k=req.top_k,
                )

            chunk_texts = [h.content for h in hits]
            contexts.append(chunk_texts)
            context_ids.append([h.chunk_id for h in hits])
            context_scores.append([h.score for h in hits])

            answer = _generate_answer(
                query=question,
                context_chunks=chunk_texts,
                model=req.generator_model,
            )
            answers.append(answer)

            logger.debug("Pergunta %d/%d processada.", i + 1, len(questions))

        # ── Fase 2: Avaliação RAGAS (em batch) ────────────────────────────────
        logger.info("Experimento %s: iniciando avaliação RAGAS...", self.experiment_id)

        ragas_scores = evaluate_with_ragas(
            questions=questions,
            answers=answers,
            contexts=contexts,
            ground_truths=ground_truths,
            llm_model=req.generator_model,
            embedding_model=req.embedding_model,
        )

        mrr_scores = compute_mrr(contexts, ground_truths)
        recall_scores = compute_recall_at_k(contexts, ground_truths, k=req.top_k)

        # ── Fase 3: Persistência no PostgreSQL ────────────────────────────────
        logger.info("Experimento %s: persistindo resultados...", self.experiment_id)

        for i, golden_q in enumerate(req.golden_questions):
            scores = ragas_scores[i]
            result = ExperimentResult(
                experiment_id=self.experiment_id,
                question=golden_q.question,
                expected_answer=golden_q.expected_answer,
                generated_answer=answers[i],
                retrieved_context=[
                    {
                        "chunk_id": cid,
                        "content": ctx,
                        "score": score,
                    }
                    for cid, ctx, score in zip(
                        context_ids[i], contexts[i], context_scores[i]
                    )
                ],
                faithfulness=scores.get("faithfulness"),
                answer_relevancy=scores.get("answer_relevancy"),
                context_precision=scores.get("context_precision"),
                context_recall=scores.get("context_recall"),
                answer_correctness=scores.get("answer_correctness"),
                mrr=mrr_scores[i],
            )
            db.add(result)

        db.commit()
        logger.info("Experimento %s concluído com sucesso.", self.experiment_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, db: Session, status: ExperimentStatus) -> None:
        experiment = db.get(Experiment, self.experiment_id)
        if experiment is None:
            return
        experiment.status = status.value
        if status == ExperimentStatus.completed:
            experiment.completed_at = datetime.now(timezone.utc)
        db.commit()


# ── RAG generation (reaproveitada da rota rag.py, sem dependência circular) ──

_SYSTEM_PROMPT = """Você é um assistente especializado em documentos institucionais brasileiros.
Use APENAS o contexto fornecido para responder à pergunta.
Se a resposta não estiver no contexto, responda: "Informação não encontrada no contexto fornecido."
Seja conciso e preciso. Responda em português do Brasil."""


def _generate_answer(query: str, context_chunks: list[str], model: str) -> str:
    from openai import OpenAI  # noqa: PLC0415

    from core.config import settings  # noqa: PLC0415

    context = "\n\n---\n\n".join(
        f"[Trecho {i + 1}]\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexto:\n{context}\n\nPergunta: {query}"},
        ],
        temperature=0,
        seed=42,
    )
    return response.choices[0].message.content or ""
