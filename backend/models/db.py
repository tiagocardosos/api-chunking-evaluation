import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    documents: Mapped[list["Document"]] = relationship(back_populates="collection")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="collection")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)  # pdf | xml_lattes
    chunking_strategy: Mapped[str] = mapped_column(String, nullable=False)
    chunk_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_overlap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)

    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unique_word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sentence_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phrase_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=_now)

    collection: Mapped["Collection"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String, nullable=False)
    chunk_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_overlap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    generator_model: Mapped[str] = mapped_column(String, nullable=False)
    retrieval_strategy: Mapped[str] = mapped_column(String, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    collection: Mapped["Collection"] = relationship(back_populates="experiments")
    results: Mapped[list["ExperimentResult"]] = relationship(back_populates="experiment")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[Optional[list[Any]]] = mapped_column(JSON, nullable=True)
    # RAGAS metrics
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevancy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_correctness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mrr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    experiment: Mapped["Experiment"] = relationship(back_populates="results")
