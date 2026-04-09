from fastapi import APIRouter, Form, HTTPException, UploadFile
from pathlib import Path

from core.chunking import get_chunker
from core.loaders.json_lattes_loader import load_json_lattes
from core.loaders.pdf_loader import load_pdf
from core.loaders.xml_loader import load_xml
from models.enums import ChunkingStrategy
from models.schemas import ChunkPreview, ChunkPreviewRequest, ChunkPreviewResponse

router = APIRouter()


@router.post("/preview", response_model=ChunkPreviewResponse)
async def preview_chunks(
    file: UploadFile,
    chunking_strategy: ChunkingStrategy = Form(...),
    chunk_size: int = Form(default=512),
    chunk_overlap: int = Form(default=50),
):
    """
    Gera um preview dos chunks sem ingerir o documento.

    Útil para validar visualmente como cada estratégia divide o texto,
    especialmente o StructureAwareChunker em XMLs Lattes.

    Retorna todos os chunks (sem limite), para inspeção completa.
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Arquivo sem nome.")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".xml", ".json"}:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão {ext!r} não suportada. Use .pdf, .xml ou .json.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # Carrega o texto adequado ao tipo de arquivo
    try:
        if ext == ".pdf":
            doc = load_pdf(file_bytes)
            text = doc.full_text
        elif ext == ".xml":
            doc = load_xml(file_bytes)
            # StructureAwareChunker recebe XML cru; os demais recebem plain text
            text = (
                doc.raw_xml
                if chunking_strategy == ChunkingStrategy.structure_aware
                else doc.plain_text
            )
        else:  # .json
            doc = load_json_lattes(file_bytes)
            text = (
                doc.raw_content
                if chunking_strategy == ChunkingStrategy.structure_aware
                else doc.plain_text
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Monta kwargs conforme a estratégia
    kwargs = _build_kwargs(chunking_strategy, chunk_size, chunk_overlap)

    try:
        chunker = get_chunker(chunking_strategy, **kwargs)
        chunks = chunker.split(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no chunking: {exc}") from exc

    return ChunkPreviewResponse(
        chunking_strategy=chunking_strategy,
        total_chunks=len(chunks),
        chunks=[
            ChunkPreview(
                chunk_index=c.chunk_index,
                content=c.content,
                chunk_metadata=c.metadata,
            )
            for c in chunks
        ],
    )


def _build_kwargs(
    strategy: ChunkingStrategy, chunk_size: int, chunk_overlap: int
) -> dict:
    if strategy in {ChunkingStrategy.fixed_size, ChunkingStrategy.recursive}:
        return {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
    if strategy in {ChunkingStrategy.sentence, ChunkingStrategy.semantic}:
        return {"max_chunk_size": chunk_size}
    if strategy == ChunkingStrategy.structure_aware:
        return {"max_chunk_size": max(chunk_size, 512)}
    return {}
