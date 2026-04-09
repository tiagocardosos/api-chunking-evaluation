"""
FixedSizeChunker
================
Divide o texto em janelas de tamanho fixo (em caracteres) com sobreposição.

Configurações do experimento (EXPERIMENT-SPEC §3):
    chunk_size  : 256 | 512 | 1024
    chunk_overlap: 0  |  50 |  128
"""
from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import register
from models.enums import ChunkingStrategy


@register(ChunkingStrategy.fixed_size)
class FixedSizeChunker(BaseChunker):
    """
    Estratégia de referência (baseline simples).

    Algoritmo:
        1. Avança um ponteiro `start` de 0 até o fim do texto.
        2. Cada chunk = texto[start : start + chunk_size].
        3. O próximo start = start + (chunk_size - chunk_overlap).
        4. Chunks com conteúdo apenas de espaços são descartados.

    Vantagens  : determinístico, sem dependências externas, rápido.
    Desvantagens: ignora fronteiras semânticas (corta palavras/frases).
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size deve ser positivo.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap não pode ser negativo.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @property
    def strategy_name(self) -> str:
        return ChunkingStrategy.fixed_size.value

    def split(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        chunks: list[ChunkData] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            content = text[start:end].strip()

            if content:
                chunks.append(
                    ChunkData(
                        content=content,
                        chunk_index=len(chunks),
                        metadata={
                            "strategy": self.strategy_name,
                            "chunk_size": self.chunk_size,
                            "chunk_overlap": self.chunk_overlap,
                            "start_char": start,
                            "end_char": end,
                        },
                    )
                )

            start += step

        return chunks
