"""
SemanticChunker
===============
Identifica fronteiras semânticas entre sentenças usando similaridade de embeddings.
Agrupa sentenças com alta coerência semântica no mesmo chunk.

Usa OpenAI embeddings (variável fixada no experimento) para detectar os pontos
de quebra — mantendo consistência com o embedding de retrieval.
"""
from __future__ import annotations

import numpy as np

from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import register
from core.chunking.sentence import split_sentences
from models.enums import ChunkingStrategy


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similaridade cosseno entre dois vetores. Retorna valor em [-1, 1]."""
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


@register(ChunkingStrategy.semantic)
class SemanticChunker(BaseChunker):
    """
    Divide o texto em chunks semanticamente coerentes usando OpenAI embeddings.

    Algoritmo:
        1. Divide em sentenças via split_sentences (pt-BR aware).
        2. Calcula embeddings para cada sentença via OpenAI (em batch).
        3. Calcula similaridade cosseno entre sentenças adjacentes:
               sim[i] = cosine(embed[i], embed[i+1])
        4. Identifica "vales" de similaridade: posições onde sim[i] cai
           abaixo do percentil `breakpoint_percentile` de todas as sims.
           Percentil baixo (ex: 25) → poucos cortes (chunks maiores).
           Percentil alto  (ex: 75) → muitos cortes (chunks menores).
        5. Agrupa sentenças do mesmo segmento semântico em um ChunkData.
        6. Proteção: segmentos maiores que `max_chunk_size` são subdivididos
           por caractere como fallback.

    Parâmetros:
        embedding_model:        modelo OpenAI (default: settings.embedding_model).
        breakpoint_percentile:  percentil [0-100] de similaridade para quebra.
        max_chunk_size:         limite de segurança em caracteres.

    Vantagens  : preserva coerência temática; não depende de separadores fixos.
    Desvantagens: requer chamadas à API OpenAI durante a ingestão (custo/latência);
                  não determinístico se o modelo mudar entre runs.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        breakpoint_percentile: int = 25,
        max_chunk_size: int = 1024,
    ) -> None:
        if not 0 <= breakpoint_percentile <= 100:
            raise ValueError("breakpoint_percentile deve estar entre 0 e 100.")

        self.embedding_model = embedding_model  # None → usa settings.embedding_model
        self.breakpoint_percentile = breakpoint_percentile
        self.max_chunk_size = max_chunk_size
        self._embedder = None  # lazy init

    def _get_embedder(self):
        if self._embedder is None:
            from core.embeddings import OpenAIEmbedder  # noqa: PLC0415

            self._embedder = OpenAIEmbedder(model=self.embedding_model)
        return self._embedder

    @property
    def strategy_name(self) -> str:
        return ChunkingStrategy.semantic.value

    def split(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        sentences = split_sentences(text)

        if len(sentences) <= 1:
            return [
                ChunkData(
                    content=text.strip(),
                    chunk_index=0,
                    metadata={
                        "strategy": self.strategy_name,
                        "sentence_count": len(sentences),
                    },
                )
            ]

        # ── Embeddings via OpenAI (batch) ─────────────────────────────────────
        embedder = self._get_embedder()
        raw_vectors = embedder.embed(sentences)
        embeddings = np.array(raw_vectors, dtype=np.float32)

        # ── Similaridades adjacentes ──────────────────────────────────────────
        similarities = np.array([
            _cosine_similarity(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ])

        # ── Limiar de quebra ──────────────────────────────────────────────────
        threshold = float(np.percentile(similarities, self.breakpoint_percentile))
        breakpoints: set[int] = {
            i + 1
            for i, sim in enumerate(similarities)
            if sim < threshold
        }

        # ── Agrupamento em chunks ─────────────────────────────────────────────
        chunks: list[ChunkData] = []
        group: list[str] = []
        group_sims: list[float] = []

        for i, sentence in enumerate(sentences):
            if i in breakpoints and group:
                chunks.extend(self._flush_group(group, group_sims, len(chunks)))
                group = []
                group_sims = []

            group.append(sentence)
            if i < len(similarities):
                group_sims.append(float(similarities[i]))

        if group:
            chunks.extend(self._flush_group(group, group_sims, len(chunks)))

        return chunks

    def _flush_group(
        self,
        sentences: list[str],
        sims: list[float],
        base_index: int,
    ) -> list[ChunkData]:
        content = " ".join(sentences)
        meta_base = {
            "strategy": self.strategy_name,
            "sentence_count": len(sentences),
            "avg_similarity": float(np.mean(sims)) if sims else None,
        }

        if len(content) <= self.max_chunk_size:
            return [ChunkData(content=content, chunk_index=base_index, metadata=meta_base)]

        # Fallback: subdivisão por caractere
        return [
            ChunkData(
                content=sub,
                chunk_index=base_index + j,
                metadata={**meta_base, "oversized_split": True, "sub_index": j},
            )
            for j, sub in enumerate(_split_by_size(content, self.max_chunk_size))
        ]


def _split_by_size(text: str, max_size: int) -> list[str]:
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]
