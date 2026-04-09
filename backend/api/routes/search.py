from fastapi import APIRouter, Depends, HTTPException

from core.embeddings import OpenAIEmbedder
from core.vector_store import VectorStore
from models.enums import RetrievalStrategy
from models.schemas import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


def get_vector_store() -> VectorStore:
    return VectorStore()


@router.post("", response_model=SearchResponse)
def search(
    body: SearchRequest,
    vs: VectorStore = Depends(get_vector_store),
):
    """
    Busca semântica ou híbrida em uma coleção.

    - **semantic**: similaridade cosseno sobre vetores densos (OpenAI).
    - **hybrid**: dense + BM25 esparso via Reciprocal Rank Fusion.
      (Etapa 5b completa: atualmente faz fallback para semântico puro.)
    """
    if not vs.collection_exists(body.collection_id):
        raise HTTPException(
            status_code=404,
            detail=f"Coleção {body.collection_id!r} não encontrada no Qdrant. "
                   "Ingira documentos primeiro.",
        )

    embedder = OpenAIEmbedder()
    query_vector = embedder.embed_query(body.query)

    if body.retrieval_strategy == RetrievalStrategy.hybrid:
        hits = vs.search_hybrid(
            collection_name=body.collection_id,
            query_vector=query_vector,
            query_text=body.query,
            top_k=body.top_k,
        )
    else:
        hits = vs.search_semantic(
            collection_name=body.collection_id,
            query_vector=query_vector,
            top_k=body.top_k,
        )

    return SearchResponse(
        query=body.query,
        results=[
            SearchResult(
                chunk_id=hit.chunk_id,
                content=hit.content,
                score=hit.score,
                chunk_metadata=hit.chunk_metadata,
            )
            for hit in hits
        ],
    )
