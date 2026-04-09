from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkData:
    """Unidade atômica de texto produzida por um chunker."""

    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError(f"Chunk {self.chunk_index} não pode ter conteúdo vazio.")


class BaseChunker(ABC):
    """
    Interface comum para todas as estratégias de chunking.

    Contrato:
    - `split` recebe texto puro (já extraído do PDF/XML) e retorna lista ordenada de ChunkData.
    - Cada ChunkData.metadata deve conter ao menos a chave "strategy".
    - Implementações não devem produzir chunks com conteúdo vazio ou apenas espaços.
    """

    @abstractmethod
    def split(self, text: str) -> list[ChunkData]:
        """Divide o texto em chunks. Retorna lista ordenada por chunk_index."""
        ...

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Identificador único da estratégia (mesmo valor usado no enum ChunkingStrategy)."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy_name!r})"
