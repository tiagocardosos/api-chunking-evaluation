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

class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    filename: str
    doc_type: DocType
    chunking_strategy: ChunkingStrategy
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    total_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: DocType
    chunking_strategy: ChunkingStrategy
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    total_chunks: int
    preview: list[ChunkPreview]


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


# ── Dashboard ─────────────────────────────────────────────────────────────────

class CorpusStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_words: int
    total_unique_words: int
    total_sentences: int
    total_phrases: int
    total_characters: int
    total_pages: int
    avg_chunk_size: float


class StrategyStats(BaseModel):
    strategy: ChunkingStrategy
    total_chunks: int
    document_count: int
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_context_recall: Optional[float] = None
    avg_answer_correctness: Optional[float] = None


class RecentExperiment(BaseModel):
    name: str
    strategy: ChunkingStrategy
    status: ExperimentStatus
    avg_answer_correctness: Optional[float] = None
    created_at: datetime


class DashboardResponse(BaseModel):
    total_collections: int
    total_documents: int
    total_experiments: int
    total_golden_questions: int
    corpus_stats: CorpusStats
    strategy_stats: list[StrategyStats]
    recent_experiments: list[RecentExperiment]


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
