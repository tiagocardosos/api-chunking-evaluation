from statistics import mean
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.experiment_runner import ExperimentRunner
from core.vector_store import VectorStore
from models.db import Collection, Experiment, ExperimentResult
from models.enums import ExperimentStatus
from models.schemas import (
    ExperimentResultSummary,
    ExperimentRunRequest,
    ExperimentRunResponse,
)

router = APIRouter()


def get_vector_store() -> VectorStore:
    return VectorStore()


# ── Iniciar experimento ───────────────────────────────────────────────────────

@router.post("/run", response_model=ExperimentRunResponse, status_code=202)
def run_experiment(
    body: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    vs: VectorStore = Depends(get_vector_store),
):
    """
    Inicia um experimento em background e retorna imediatamente.

    HTTP 202 Accepted: o experimento foi enfileirado mas ainda não concluído.
    Use GET /experiments/{id} para acompanhar o status e obter os resultados.

    Fluxo:
        1. Valida que a collection existe.
        2. Cria registro Experiment no Postgres (status=pending).
        3. Agenda a execução em background (embedding → RAG → RAGAS).
        4. Retorna experiment_id + status=pending imediatamente.
    """
    # Valida collection
    collection = db.get(Collection, body.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=404,
            detail=f"Coleção {body.collection_id!r} não encontrada.",
        )

    if not vs.collection_exists(body.collection_id):
        raise HTTPException(
            status_code=422,
            detail="Coleção existe no Postgres mas não tem documentos indexados no Qdrant. "
                   "Ingira documentos antes de rodar o experimento.",
        )

    if not body.golden_questions:
        raise HTTPException(
            status_code=422,
            detail="golden_questions não pode ser vazio.",
        )

    # Cria registro do experimento
    experiment = Experiment(
        name=body.name,
        collection_id=body.collection_id,
        chunking_strategy=body.chunking_strategy.value,
        chunk_size=body.chunk_size,
        chunk_overlap=body.chunk_overlap,
        embedding_model=body.embedding_model,
        generator_model=body.generator_model,
        retrieval_strategy=body.retrieval_strategy.value,
        top_k=body.top_k,
        status=ExperimentStatus.pending.value,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    # Agenda execução em background
    from core.database import SessionLocal  # noqa: PLC0415

    runner = ExperimentRunner(
        experiment_id=experiment.id,
        request=body,
        db_factory=SessionLocal,
        vector_store=VectorStore(),  # nova instância para o background thread
    )
    background_tasks.add_task(runner.run)

    return ExperimentRunResponse(
        experiment_id=experiment.id,
        name=experiment.name,
        status=ExperimentStatus.pending,
        total_questions=len(body.golden_questions),
        results=[],
    )


# ── Consultar experimento ─────────────────────────────────────────────────────

@router.get("/{experiment_id}", response_model=ExperimentRunResponse)
def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """
    Retorna o estado atual de um experimento com todos os resultados disponíveis.

    Enquanto status=running, results pode estar parcialmente preenchido.
    Quando status=completed, results contém todas as perguntas com métricas.
    """
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experimento não encontrado.")

    results = (
        db.query(ExperimentResult)
        .filter(ExperimentResult.experiment_id == experiment_id)
        .order_by(ExperimentResult.created_at)
        .all()
    )

    summaries = [
        ExperimentResultSummary(
            question=r.question,
            generated_answer=r.generated_answer,
            faithfulness=r.faithfulness,
            answer_relevancy=r.answer_relevancy,
            context_precision=r.context_precision,
            context_recall=r.context_recall,
            answer_correctness=r.answer_correctness,
            mrr=r.mrr,
        )
        for r in results
    ]

    return ExperimentRunResponse(
        experiment_id=experiment.id,
        name=experiment.name,
        status=ExperimentStatus(experiment.status),
        total_questions=len(summaries),
        avg_faithfulness=_avg(r.faithfulness for r in results),
        avg_answer_relevancy=_avg(r.answer_relevancy for r in results),
        avg_context_precision=_avg(r.context_precision for r in results),
        avg_context_recall=_avg(r.context_recall for r in results),
        avg_answer_correctness=_avg(r.answer_correctness for r in results),
        results=summaries,
    )


# ── Listar experimentos ───────────────────────────────────────────────────────

@router.get("", response_model=list[ExperimentRunResponse])
def list_experiments(
    collection_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Lista experimentos, opcionalmente filtrados por coleção.
    Retorna apenas metadados (sem results), para visão geral.
    """
    query = db.query(Experiment).order_by(Experiment.created_at.desc())
    if collection_id:
        query = query.filter(Experiment.collection_id == collection_id)

    experiments = query.all()

    return [
        ExperimentRunResponse(
            experiment_id=e.id,
            name=e.name,
            status=ExperimentStatus(e.status),
            total_questions=0,
            results=[],
        )
        for e in experiments
    ]


# ── Helper ────────────────────────────────────────────────────────────────────

def _avg(values) -> Optional[float]:
    """Média ignorando None. Retorna None se não houver nenhum valor válido."""
    valid = [v for v in values if v is not None]
    return round(mean(valid), 4) if valid else None
