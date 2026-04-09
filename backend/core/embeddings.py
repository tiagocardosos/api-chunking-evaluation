"""
Embeddings
==========
Geração de embeddings via API OpenAI.

O embedding é uma variável FIXADA no experimento (EXPERIMENT-SPEC §2).
Modelo padrão: text-embedding-3-small (1536 dims).

Batching automático: a API aceita até 2048 inputs por chamada;
este módulo usa batches de 512 para segurança.
"""
from __future__ import annotations

from core.config import settings

# Mapeamento modelo → dimensão do vetor
MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_BATCH_SIZE = 512


def get_embedding_dim(model: str) -> int:
    if model not in MODEL_DIMENSIONS:
        raise ValueError(
            f"Modelo desconhecido: {model!r}. "
            f"Disponíveis: {sorted(MODEL_DIMENSIONS.keys())}"
        )
    return MODEL_DIMENSIONS[model]


class OpenAIEmbedder:
    """
    Wrapper sobre o endpoint de embeddings da OpenAI.

    Uso:
        embedder = OpenAIEmbedder()
        vectors = embedder.embed(["chunk 1", "chunk 2"])
        query_vec = embedder.embed_query("minha pergunta")
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.embedding_model
        if self.model not in MODEL_DIMENSIONS:
            raise ValueError(f"Modelo de embedding não suportado: {self.model!r}")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # noqa: PLC0415

            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    @property
    def dimensions(self) -> int:
        return MODEL_DIMENSIONS[self.model]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings para uma lista de textos.

        Args:
            texts: lista de strings (chunks de texto).

        Returns:
            Lista de vetores float, na mesma ordem da entrada.
        """
        if not texts:
            return []

        client = self._get_client()
        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            response = client.embeddings.create(input=batch, model=self.model)
            all_vectors.extend(item.embedding for item in response.data)

        return all_vectors

    def embed_query(self, text: str) -> list[float]:
        """Embedding de um único texto (para queries em tempo de busca)."""
        return self.embed([text])[0]
