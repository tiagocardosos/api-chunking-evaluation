from statistics import mean
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from models.db import Chunk, Collection, Document, Experiment, ExperimentResult
from models.enums import ChunkingStrategy, ExperimentStatus
from models.schemas import (
    CorpusStats,
    DashboardResponse,
    RecentExperiment,
    StrategyStats,
)

router = APIRouter()

RECENT_EXPERIMENTS_LIMIT = 5


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Retorna estatísticas agregadas para o dashboard do frontend."""
    total_collections = db.query(func.count(Collection.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    total_experiments = db.query(func.count(Experiment.id)).scalar() or 0

    total_golden_questions = (
        db.query(func.count(func.distinct(ExperimentResult.question))).scalar() or 0
    )

    corpus = _build_corpus_stats(db)
    strategies = _build_strategy_stats(db)
    recent = _build_recent_experiments(db)

    return DashboardResponse(
        total_collections=total_collections,
        total_documents=total_documents,
        total_experiments=total_experiments,
        total_golden_questions=total_golden_questions,
        corpus_stats=corpus,
        strategy_stats=strategies,
        recent_experiments=recent,
    )


def _build_corpus_stats(db: Session) -> CorpusStats:
    row = db.query(
        func.coalesce(func.sum(Document.word_count), 0),
        func.coalesce(func.sum(Document.unique_word_count), 0),
        func.coalesce(func.sum(Document.sentence_count), 0),
        func.coalesce(func.sum(Document.phrase_count), 0),
        func.coalesce(func.sum(Document.char_count), 0),
        func.coalesce(func.sum(Document.page_count), 0),
        func.coalesce(func.sum(Document.total_chunks), 0),
        func.count(Document.id),
    ).one()

    total_words, total_unique, total_sentences, total_phrases = row[0], row[1], row[2], row[3]
    total_chars, total_pages, total_chunks, total_docs = row[4], row[5], row[6], row[7]

    avg_chunk_size_row = db.query(
        func.avg(func.length(Chunk.content))
    ).scalar()
    avg_chunk_size = round(float(avg_chunk_size_row), 1) if avg_chunk_size_row else 0.0

    return CorpusStats(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_words=total_words,
        total_unique_words=total_unique,
        total_sentences=total_sentences,
        total_phrases=total_phrases,
        total_characters=total_chars,
        total_pages=total_pages,
        avg_chunk_size=avg_chunk_size,
    )


def _build_strategy_stats(db: Session) -> list[StrategyStats]:
    strategy_rows = (
        db.query(
            Document.chunking_strategy,
            func.sum(Document.total_chunks),
            func.count(Document.id),
        )
        .group_by(Document.chunking_strategy)
        .all()
    )

    results: list[StrategyStats] = []
    for strategy_value, chunk_sum, doc_count in strategy_rows:
        try:
            strategy_enum = ChunkingStrategy(strategy_value)
        except ValueError:
            continue

        metrics = _latest_experiment_metrics(db, strategy_value)

        results.append(StrategyStats(
            strategy=strategy_enum,
            total_chunks=chunk_sum or 0,
            document_count=doc_count or 0,
            **metrics,
        ))

    return results


def _latest_experiment_metrics(db: Session, strategy_value: str) -> dict:
    """Busca métricas médias do experimento mais recente completado para uma estratégia."""
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.chunking_strategy == strategy_value,
            Experiment.status == ExperimentStatus.completed.value,
        )
        .order_by(Experiment.completed_at.desc())
        .first()
    )
    if experiment is None:
        return {}

    exp_results = (
        db.query(ExperimentResult)
        .filter(ExperimentResult.experiment_id == experiment.id)
        .all()
    )
    if not exp_results:
        return {}

    return {
        "avg_faithfulness": _avg(r.faithfulness for r in exp_results),
        "avg_answer_relevancy": _avg(r.answer_relevancy for r in exp_results),
        "avg_context_precision": _avg(r.context_precision for r in exp_results),
        "avg_context_recall": _avg(r.context_recall for r in exp_results),
        "avg_answer_correctness": _avg(r.answer_correctness for r in exp_results),
    }


def _build_recent_experiments(db: Session) -> list[RecentExperiment]:
    experiments = (
        db.query(Experiment)
        .order_by(Experiment.created_at.desc())
        .limit(RECENT_EXPERIMENTS_LIMIT)
        .all()
    )

    results: list[RecentExperiment] = []
    for exp in experiments:
        try:
            strategy_enum = ChunkingStrategy(exp.chunking_strategy)
        except ValueError:
            continue

        avg_correctness: Optional[float] = None
        if exp.status == ExperimentStatus.completed.value:
            exp_results = (
                db.query(ExperimentResult)
                .filter(ExperimentResult.experiment_id == exp.id)
                .all()
            )
            avg_correctness = _avg(r.answer_correctness for r in exp_results)

        results.append(RecentExperiment(
            name=exp.name,
            strategy=strategy_enum,
            status=ExperimentStatus(exp.status),
            avg_answer_correctness=avg_correctness,
            created_at=exp.created_at,
        ))

    return results


def _avg(values) -> Optional[float]:
    valid = [v for v in values if v is not None]
    return round(mean(valid), 4) if valid else None
