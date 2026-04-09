"""
VectorStore
===========
Wrapper sobre o Qdrant para operações do experimento.

Responsabilidades:
    - Criar/obter coleções (uma por collection_id do experimento)
    - Inserir chunks com seus embeddings e payload
    - Busca semântica (dense) e híbrida (dense + sparse BM25)
    - Deletar coleções

Estrutura de um ponto no Qdrant:
    id      : chunk_id (UUID como string)
    vector  : {"dense": [...]}
    payload : {
        "chunk_id"          : str,
        "document_id"       : str,
        "content"           : str,
        "chunk_index"       : int,
        "chunking_strategy" : str,
        "chunk_metadata"    : dict,
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from core.config import settings
from core.embeddings import get_embedding_dim

# Nome do vetor denso dentro de cada coleção
_DENSE_VECTOR = "dense"


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    content: str
    score: float
    chunk_metadata: dict[str, Any]


class VectorStore:
    """
    Interface de alto nível para o Qdrant.

    Instanciação:
        vs = VectorStore()                     # usa settings.qdrant_url
        vs = VectorStore(url="http://...")     # URL explícita
    """

    def __init__(self, url: str | None = None) -> None:
        self._client = QdrantClient(url=url or settings.qdrant_url)

    # ── Coleções ──────────────────────────────────────────────────────────────

    def get_or_create_collection(
        self,
        collection_name: str,
        embedding_model: str | None = None,
    ) -> None:
        """
        Cria a coleção no Qdrant se ainda não existir.

        Args:
            collection_name: nome da coleção (= collection_id do Postgres).
            embedding_model: modelo usado para definir o tamanho do vetor.
                             Default: settings.embedding_model.
        """
        model = embedding_model or settings.embedding_model
        vector_size = get_embedding_dim(model)

        existing = {c.name for c in self._client.get_collections().collections}
        if collection_name in existing:
            return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config={
                _DENSE_VECTOR: qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                )
            },
        )

    def delete_collection(self, collection_name: str) -> None:
        self._client.delete_collection(collection_name)

    def collection_exists(self, collection_name: str) -> bool:
        existing = {c.name for c in self._client.get_collections().collections}
        return collection_name in existing

    # ── Ingestão ──────────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        collection_name: str,
        chunk_ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        """
        Insere ou atualiza chunks na coleção.

        Args:
            collection_name : coleção de destino.
            chunk_ids       : UUIDs dos chunks (alinhados com vectors e payloads).
            vectors         : embeddings densos.
            payloads        : metadados de cada chunk (incluindo content).
        """
        if not chunk_ids:
            return

        points = [
            qmodels.PointStruct(
                id=chunk_id,
                vector={_DENSE_VECTOR: vector},
                payload=payload,
            )
            for chunk_id, vector, payload in zip(chunk_ids, vectors, payloads)
        ]

        self._client.upsert(collection_name=collection_name, points=points)

    def delete_points(self, collection_name: str, chunk_ids: list[str]) -> None:
        """Remove pontos específicos da coleção (usado para rollback)."""
        if not chunk_ids:
            return
        self._client.delete(
            collection_name=collection_name,
            points_selector=qmodels.PointIdsList(points=chunk_ids),
        )

    # ── Busca ─────────────────────────────────────────────────────────────────

    def search_semantic(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 5,
        filter_document_id: str | None = None,
    ) -> list[SearchHit]:
        """
        Busca semântica por similaridade cosseno (vetor denso).

        Args:
            collection_name    : coleção a consultar.
            query_vector       : embedding da query.
            top_k              : número de resultados.
            filter_document_id : se informado, restringe a busca a um documento.

        Returns:
            Lista de SearchHit ordenada por score decrescente.
        """
        query_filter = None
        if filter_document_id:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=filter_document_id),
                    )
                ]
            )

        results = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using=_DENSE_VECTOR,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        return [_result_to_hit(r) for r in results.points]

    def search_hybrid(
        self,
        collection_name: str,
        query_vector: list[float],
        query_text: str,
        top_k: int = 5,
    ) -> list[SearchHit]:
        """
        Busca híbrida: combina score semântico (denso) com BM25 (esparso)
        via Reciprocal Rank Fusion (RRF).

        Nota: requer que a coleção tenha sido criada com suporte a vetores
        esparsos. Esta implementação usa apenas o vetor denso como fallback
        se vetores esparsos não estiverem disponíveis.

        A integração completa com sparse vectors (Qdrant fastembed BM25)
        é implementada na Etapa 5b.
        """
        # Fallback para semântico puro enquanto sparse não está configurado
        # TODO (Etapa 5b): adicionar sparse vectors BM25
        return self.search_semantic(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k,
        )

    def get_chunk_by_id(
        self, collection_name: str, chunk_id: str
    ) -> SearchHit | None:
        results = self._client.retrieve(
            collection_name=collection_name,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return None
        return _result_to_hit(results[0])


def _result_to_hit(point: Any) -> SearchHit:
    payload = point.payload or {}
    return SearchHit(
        chunk_id=str(point.id),
        document_id=payload.get("document_id", ""),
        content=payload.get("content", ""),
        score=getattr(point, "score", 0.0),
        chunk_metadata=payload.get("chunk_metadata", {}),
    )
