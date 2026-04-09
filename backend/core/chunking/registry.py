"""
Registry de estratégias de chunking.

Uso:
    @register(ChunkingStrategy.fixed_size)
    class FixedSizeChunker(BaseChunker):
        ...

    chunker = get_chunker(ChunkingStrategy.fixed_size, chunk_size=512)
"""
from models.enums import ChunkingStrategy
from core.chunking.base import BaseChunker

_registry: dict[str, type[BaseChunker]] = {}


def register(strategy: ChunkingStrategy):
    """Decorador que registra um chunker para a estratégia dada."""

    def decorator(cls: type[BaseChunker]) -> type[BaseChunker]:
        _registry[strategy.value] = cls
        return cls

    return decorator


def get_chunker(strategy: ChunkingStrategy | str, **kwargs) -> BaseChunker:
    """
    Instancia o chunker registrado para a estratégia indicada.

    Args:
        strategy: enum ChunkingStrategy ou sua string equivalente.
        **kwargs: parâmetros repassados ao construtor do chunker.

    Raises:
        ValueError: se a estratégia não estiver registrada.
    """
    key = strategy.value if isinstance(strategy, ChunkingStrategy) else strategy
    if key not in _registry:
        available = sorted(_registry.keys())
        raise ValueError(
            f"Estratégia desconhecida: {key!r}. "
            f"Disponíveis: {available}"
        )
    return _registry[key](**kwargs)


def list_strategies() -> list[str]:
    """Retorna os nomes de todas as estratégias registradas."""
    return sorted(_registry.keys())
