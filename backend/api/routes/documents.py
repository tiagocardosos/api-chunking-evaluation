import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.ingestor import ingest_document
from core.vector_store import VectorStore
from models.db import Chunk, Document
from models.enums import ChunkingStrategy
from models.schemas import ChunkPreview, ChunksListResponse, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_vector_store() -> VectorStore:
    return VectorStore()


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(
    file: UploadFile,
    collection_id: str = Form(...),
    chunking_strategy: ChunkingStrategy = Form(...),
    chunk_size: int = Form(default=512),
    chunk_overlap: int = Form(default=50),
    embedding_model: str = Form(default=None),
    db: Session = Depends(get_db),
    vs: VectorStore = Depends(get_vector_store),
):
    """
    Ingere um documento (PDF ou XML Lattes) no sistema RAG.

    - Detecta o tipo automaticamente pela extensão.
    - Aplica a estratégia de chunking escolhida.
    - Gera embeddings via OpenAI e indexa no Qdrant.
    - Persiste metadados no PostgreSQL.
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Arquivo sem nome.")

    allowed_extensions = {".pdf", ".xml", ".json"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão {ext!r} não suportada. Use .pdf, .xml ou .json.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    model = embedding_model or settings.embedding_model

    try:
        response = ingest_document(
            file_bytes=file_bytes,
            filename=file.filename,
            collection_id=collection_id,
            chunking_strategy=chunking_strategy,
            embedding_model=model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            db=db,
            vector_store=vs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Erro inesperado durante ingestão de '%s'", file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno durante a ingestão: {type(exc).__name__}: {exc}",
        ) from exc

    return response


@router.get("/{document_id}/chunks", response_model=ChunksListResponse)
def list_chunks(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Retorna todos os chunks de um documento (útil para validar o StructureAwareChunker).
    """
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .all()
    )

    return ChunksListResponse(
        document_id=document_id,
        total_chunks=document.total_chunks,
        chunks=[
            ChunkPreview(
                chunk_index=c.chunk_index,
                content=c.content,
                chunk_metadata=c.chunk_metadata or {},
            )
            for c in chunks
        ],
    )
