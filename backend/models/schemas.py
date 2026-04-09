from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from models.enums import ChunkingStrategy, DocType, ExperimentStatus, RetrievalStrategy


# ── Shared ────────────────────────────────────────────────────────────────────

class ChunkPreview(BaseModel):
    chunk_index: int
    content: str
    chunk_metadata: dict[str, Any] = {}


# ── Collections ───────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Documents ─────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: DocType
    total_chunks: int
    preview: list[ChunkPreview]  # primeiros 3 chunks


class ChunksListResponse(BaseModel):
    document_id: str
    total_chunks: int
    chunks: list[ChunkPreview]


# ── Chunking preview (sem ingestão) ───────────────────────────────────────────

class ChunkPreviewRequest(BaseModel):
    chunking_strategy: ChunkingStrategy
    chunk_size: Optional[int] = Field(default=512, ge=64, le=2048)
    chunk_overlap: Optional[int] = Field(default=50, ge=0, le=512)


class ChunkPreviewResponse(BaseModel):
    chunking_strategy: ChunkingStrategy
    total_chunks: int
    chunks: list[ChunkPreview]


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    collection_id: str
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.semantic
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    chunk_metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


# ── RAG ───────────────────────────────────────────────────────────────────────

class RagChatRequest(BaseModel):
    query: str
    collection_id: str
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.semantic
    top_k: int = Field(default=5, ge=1, le=20)
    generator_model: Optional[str] = None  # sobrescreve o default de settings


class RagChatResponse(BaseModel):
    query: str
    answer: str
    context: list[SearchResult]
    latency_ms: float


# ── Experiments ───────────────────────────────────────────────────────────────

class GoldenQuestion(BaseModel):
    question: str
    expected_answer: Optional[str] = None
    question_type: Optional[str] = None  # factual | inferential


class ExperimentRunRequest(BaseModel):
    name: str
    collection_id: str
    chunking_strategy: ChunkingStrategy
    chunk_size: Optional[int] = Field(default=512, ge=64, le=2048)
    chunk_overlap: Optional[int] = Field(default=50, ge=0, le=512)
    embedding_model: str = "text-embedding-3-small"
    generator_model: str = "gpt-4o-mini"
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.semantic
    top_k: int = Field(default=5, ge=1, le=20)
    golden_questions: list[GoldenQuestion]


class ExperimentResultSummary(BaseModel):
    question: str
    generated_answer: str
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_correctness: Optional[float] = None
    mrr: Optional[float] = None


class ExperimentRunResponse(BaseModel):
    experiment_id: str
    name: str
    status: ExperimentStatus
    total_questions: int
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_context_recall: Optional[float] = None
    avg_answer_correctness: Optional[float] = None
    results: list[ExperimentResultSummary]
