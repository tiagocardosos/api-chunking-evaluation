"""
Ingestor
========
Orquestra o pipeline completo de ingestão de um documento:

    1. Valida que a coleção existe no PostgreSQL.
    2. Detecta tipo (PDF | XML Lattes) pela extensão.
    3. Carrega texto com o loader adequado.
    4. Aplica a estratégia de chunking escolhida.
    5. Gera embeddings para cada chunk via OpenAI.
    6. Indexa vetores no Qdrant.
    7. Persiste chunks + metadados no PostgreSQL (só após Qdrant OK).
    8. Retorna IngestResponse com document_id, total_chunks e preview.

Ordem intencional (6 antes de 7):
    Se o Qdrant falhar, não gravamos nada no PostgreSQL — evita registros
    órfãos sem vetores. Se o PostgreSQL falhar após o Qdrant, tentamos
    deletar os pontos inseridos (best-effort rollback).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from core.chunking import get_chunker
from core.embeddings import OpenAIEmbedder
from core.loaders.json_lattes_loader import load_json_lattes
from core.loaders.pdf_loader import load_pdf
from core.loaders.xml_loader import load_xml
from core.text_stats import compute_text_stats
from core.vector_store import VectorStore
from models.db import Chunk, Collection, Document
from models.enums import ChunkingStrategy, DocType
from models.schemas import ChunkPreview, IngestResponse

logger = logging.getLogger(__name__)


def ingest_document(
    *,
    file_bytes: bytes,
    filename: str,
    collection_id: str,
    chunking_strategy: ChunkingStrategy,
    embedding_model: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    db: Session,
    vector_store: VectorStore,
) -> IngestResponse:
    # ── 1. Validar coleção ───────────────────────────────────────────────────
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise ValueError(
            f"Coleção '{collection_id}' não encontrada. "
            "Crie a coleção via POST /collections antes de ingerir documentos."
        )

    # ── 2-3. Detectar tipo e carregar texto ──────────────────────────────────
    doc_type, text, page_count = _load(file_bytes, filename, chunking_strategy)

    # ── 2b. Estatísticas textuais para o dashboard ───────────────────────────
    text_stats = compute_text_stats(text)

    # ── 4. Chunking ──────────────────────────────────────────────────────────
    chunker_kwargs = _build_chunker_kwargs(chunking_strategy, chunk_size, chunk_overlap)
    chunker = get_chunker(chunking_strategy, **chunker_kwargs)
    chunk_data_list = chunker.split(text)

    if not chunk_data_list:
        raise ValueError("O documento não produziu nenhum chunk após o processamento.")

    logger.info(
        "Documento '%s' → %d chunks (estratégia=%s, chunk_size=%d)",
        filename, len(chunk_data_list), chunking_strategy.value, chunk_size,
    )

    # ── 5. Gerar embeddings (batch) ───────────────────────────────────────────
    embedder = OpenAIEmbedder(model=embedding_model)
    contents = [c.content for c in chunk_data_list]
    vectors = embedder.embed(contents)

    # ── 6. Garantir coleção Qdrant + indexar (ANTES do commit no Postgres) ───
    vector_store.get_or_create_collection(
        collection_name=collection_id,
        embedding_model=embedding_model,
    )

    document_id = str(uuid.uuid4())
    chunk_ids = [str(uuid.uuid4()) for _ in chunk_data_list]

    payloads = [
        {
            "chunk_id": cid,
            "document_id": document_id,
            "content": chunk_data.content,
            "chunk_index": chunk_data.chunk_index,
            "chunking_strategy": chunking_strategy.value,
            "chunk_metadata": chunk_data.metadata,
        }
        for cid, chunk_data in zip(chunk_ids, chunk_data_list)
    ]

    vector_store.upsert_chunks(
        collection_name=collection_id,
        chunk_ids=chunk_ids,
        vectors=vectors,
        payloads=payloads,
    )

    # ── 7. Persistir no PostgreSQL (após Qdrant OK) ───────────────────────────
    db_document = Document(
        id=document_id,
        collection_id=collection_id,
        filename=filename,
        doc_type=doc_type.value,
        chunking_strategy=chunking_strategy.value,
        chunk_size=chunk_size if chunking_strategy in (
            ChunkingStrategy.fixed_size, ChunkingStrategy.recursive
        ) else None,
        chunk_overlap=chunk_overlap if chunking_strategy in (
            ChunkingStrategy.fixed_size, ChunkingStrategy.recursive
        ) else None,
        total_chunks=len(chunk_data_list),
        word_count=text_stats.word_count,
        unique_word_count=text_stats.unique_word_count,
        sentence_count=text_stats.sentence_count,
        phrase_count=text_stats.phrase_count,
        char_count=text_stats.char_count,
        page_count=page_count,
    )
    db.add(db_document)
    db.add_all([
        Chunk(
            id=cid,
            document_id=document_id,
            content=chunk_data.content,
            chunk_index=chunk_data.chunk_index,
            chunk_metadata=chunk_data.metadata,
        )
        for cid, chunk_data in zip(chunk_ids, chunk_data_list)
    ])

    try:
        db.commit()
    except Exception as db_exc:
        # Qdrant já foi inserido — tenta rollback best-effort
        logger.error("Falha no commit PostgreSQL após Qdrant OK. Tentando limpar Qdrant.")
        _try_delete_qdrant_points(vector_store, collection_id, chunk_ids)
        raise ValueError(f"Erro ao persistir no banco de dados: {db_exc}") from db_exc

    db.refresh(db_document)

    # ── 8. Montar resposta ────────────────────────────────────────────────────
    preview = [
        ChunkPreview(
            chunk_index=c.chunk_index,
            content=c.content,
            chunk_metadata=c.metadata,
        )
        for c in chunk_data_list[:3]
    ]

    return IngestResponse(
        document_id=document_id,
        filename=filename,
        doc_type=doc_type,
        chunking_strategy=chunking_strategy,
        chunk_size=db_document.chunk_size,
        chunk_overlap=db_document.chunk_overlap,
        total_chunks=len(chunk_data_list),
        preview=preview,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(
    file_bytes: bytes,
    filename: str,
    strategy: ChunkingStrategy,
) -> tuple[DocType, str, int | None]:
    """
    Detecta tipo pelo nome do arquivo e extrai texto.

    Retorna (doc_type, texto, page_count). page_count é preenchido
    apenas para PDFs; XML/JSON retornam None.

    Para XML Lattes:
        - StructureAwareChunker recebe raw_xml (precisa das tags para parsear).
        - Todas as outras estratégias recebem plain_text (atributos serializados
          em texto legível), pois tags XML nos chunks prejudicam embeddings e retrieval.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        doc = load_pdf(file_bytes)
        return DocType.pdf, doc.full_text, doc.total_pages

    if ext == ".xml":
        doc = load_xml(file_bytes)
        text = (
            doc.raw_xml
            if strategy == ChunkingStrategy.structure_aware
            else doc.plain_text
        )
        return DocType.xml_lattes, text, None

    if ext == ".json":
        doc = load_json_lattes(file_bytes)
        text = (
            doc.raw_content
            if strategy == ChunkingStrategy.structure_aware
            else doc.plain_text
        )
        return DocType.json_lattes, text, None

    raise ValueError(
        f"Tipo de arquivo não suportado: {ext!r}. "
        "Use .pdf para editais EMBRAPII ou .json/.xml para currículos Lattes."
    )


def _build_chunker_kwargs(
    strategy: ChunkingStrategy,
    chunk_size: int,
    chunk_overlap: int,
) -> dict:
    if strategy in (ChunkingStrategy.fixed_size, ChunkingStrategy.recursive):
        return {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}

    if strategy in (ChunkingStrategy.sentence, ChunkingStrategy.semantic):
        return {"max_chunk_size": chunk_size}

    if strategy == ChunkingStrategy.structure_aware:
        return {"max_chunk_size": max(chunk_size, 512)}

    return {}


def _try_delete_qdrant_points(
    vector_store: VectorStore,
    collection_name: str,
    chunk_ids: list[str],
) -> None:
    """Best-effort: remove pontos do Qdrant se o commit no Postgres falhou."""
    try:
        vector_store.delete_points(collection_name, chunk_ids)
        logger.info("Rollback Qdrant: %d pontos removidos.", len(chunk_ids))
    except Exception as exc:
        logger.warning("Rollback Qdrant falhou (inconsistência possível): %s", exc)
