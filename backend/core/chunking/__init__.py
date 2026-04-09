# Importa todos os chunkers para disparar os decoradores @register
from core.chunking import (  # noqa: F401
    fixed_size,
    recursive,
    semantic,
    sentence,
    structure_aware,
)
from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import get_chunker, list_strategies, register

__all__ = [
    "BaseChunker",
    "ChunkData",
    "get_chunker",
    "list_strategies",
    "register",
]
