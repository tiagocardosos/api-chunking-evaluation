"""
RecursiveCharacterChunker
=========================
Divide o texto tentando, em ordem de prioridade, manter:
  parágrafos → frases → cláusulas → palavras intactas.

Usa LangChain RecursiveCharacterTextSplitter internamente.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import register
from models.enums import ChunkingStrategy

# Hierarquia de separadores otimizada para textos acadêmicos em português.
# A ordem importa: tenta o primeiro antes de recuar para o próximo.
_DEFAULT_SEPARATORS: list[str] = [
    "\n\n",   # parágrafos (maior coerência semântica)
    "\n",     # quebra de linha simples
    ". ",     # fim de frase seguido de espaço
    "! ",
    "? ",
    "; ",     # ponto e vírgula (listas, enumerações)
    ", ",     # vírgula
    " ",      # palavra
    "",       # caractere (último recurso)
]


@register(ChunkingStrategy.recursive)
class RecursiveCharacterChunker(BaseChunker):
    """
    Estratégia hierárquica: nunca corta no meio de uma unidade semântica
    maior enquanto houver uma menor disponível como separador.

    Baseado em: LangChain RecursiveCharacterTextSplitter.

    Vantagens  : melhor preservação de frases vs FixedSize; leve.
    Desvantagens: ainda usa caracteres como unidade, ignora semântica profunda.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or _DEFAULT_SEPARATORS

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            keep_separator=False,
        )

    @property
    def strategy_name(self) -> str:
        return ChunkingStrategy.recursive.value

    def split(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        raw_chunks = self._splitter.split_text(text)

        return [
            ChunkData(
                content=chunk.strip(),
                chunk_index=i,
                metadata={
                    "strategy": self.strategy_name,
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "actual_length": len(chunk.strip()),
                },
            )
            for i, chunk in enumerate(raw_chunks)
            if chunk.strip()
        ]
