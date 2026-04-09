"""
SentenceChunker
===============
Divide o texto em sentenças e as agrupa em chunks respeitando um tamanho máximo.
Mantém sobreposição em nível de sentença (não de caractere).

Otimizado para português: reconhece abreviações comuns e evita falsos splits.
"""
import re

from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import register
from models.enums import ChunkingStrategy

# Abreviações em português que precedem '.' sem encerrar a frase
_PT_ABBREVIATIONS: frozenset[str] = frozenset({
    # títulos e tratamentos
    "dr", "dra", "prof", "profa", "sr", "sra", "srta", "eng", "arq",
    # referências acadêmicas
    "art", "fig", "tab", "eq", "ref", "op", "cit", "ibid", "apud",
    "vol", "núm", "num", "p", "pp", "ed", "org", "coord",
    # meses
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
    # outros
    "etc", "obs", "cf", "vs",
})

# Padrão para detectar fim de sentença: pontuação seguida de espaço + maiúscula
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÃÂÊÔÇÜ\d])')

# Marcador temporário para proteger abreviações durante o split
_ABBR_MARKER = "\x00"


def split_sentences(text: str) -> list[str]:
    """
    Divide texto em sentenças respeitando abreviações em português.

    Etapas:
        1. Substitui '.' após abreviações conhecidas por um marcador invisível.
        2. Aplica regex de fronteira de sentença.
        3. Restaura os pontos das abreviações.
    """
    protected = text

    # Protege abreviações: "Dr." → "Dr\x00"
    for abbr in _PT_ABBREVIATIONS:
        for variant in (abbr, abbr.capitalize(), abbr.upper()):
            protected = re.sub(
                rf'\b{re.escape(variant)}\.',
                f'{variant}{_ABBR_MARKER}',
                protected,
            )

    raw_parts = _SENTENCE_BOUNDARY.split(protected)

    # Restaura marcadores e limpa
    return [
        part.replace(_ABBR_MARKER, ".").strip()
        for part in raw_parts
        if part.replace(_ABBR_MARKER, ".").strip()
    ]


@register(ChunkingStrategy.sentence)
class SentenceChunker(BaseChunker):
    """
    Agrupa sentenças em chunks sem ultrapassar `max_chunk_size` caracteres.

    Algoritmo:
        1. Divide o texto em sentenças via `split_sentences`.
        2. Acumula sentenças num buffer até que a próxima ultrapasse o limite.
        3. Ao fechar um chunk, os últimos `overlap_sentences` ficam no próximo.

    Parâmetros:
        max_chunk_size:    limite de caracteres por chunk (default 512).
        overlap_sentences: sentenças de sobreposição entre chunks (default 1).
                           0 = sem sobreposição.

    Vantagens  : preserva frases completas; overlap semântico natural.
    Desvantagens: chunks têm tamanhos variáveis; sem garantia de tamanho mínimo.
    """

    def __init__(self, max_chunk_size: int = 512, overlap_sentences: int = 1) -> None:
        if max_chunk_size <= 0:
            raise ValueError("max_chunk_size deve ser positivo.")
        if overlap_sentences < 0:
            raise ValueError("overlap_sentences não pode ser negativo.")

        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences

    @property
    def strategy_name(self) -> str:
        return ChunkingStrategy.sentence.value

    def split(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        sentences = split_sentences(text)
        if not sentences:
            return []

        # Frase única que já excede o limite → devolve como chunk único
        if len(sentences) == 1:
            return [
                ChunkData(
                    content=sentences[0],
                    chunk_index=0,
                    metadata={
                        "strategy": self.strategy_name,
                        "sentence_count": 1,
                        "max_chunk_size": self.max_chunk_size,
                    },
                )
            ]

        chunks: list[ChunkData] = []
        buffer: list[str] = []
        buffer_len: int = 0

        for sentence in sentences:
            sent_len = len(sentence)
            # +1 simula o espaço separador entre sentenças
            projected_len = buffer_len + sent_len + (1 if buffer else 0)

            if projected_len > self.max_chunk_size and buffer:
                chunks.append(self._make_chunk(buffer, len(chunks)))

                # Overlap: mantém últimas N sentenças no próximo chunk
                if self.overlap_sentences > 0:
                    buffer = buffer[-self.overlap_sentences :]
                    buffer_len = sum(len(s) for s in buffer) + max(0, len(buffer) - 1)
                else:
                    buffer = []
                    buffer_len = 0

            buffer.append(sentence)
            buffer_len += sent_len + (1 if len(buffer) > 1 else 0)

        # Flush do buffer final
        if buffer:
            chunks.append(self._make_chunk(buffer, len(chunks)))

        return chunks

    def _make_chunk(self, sentences: list[str], index: int) -> ChunkData:
        return ChunkData(
            content=" ".join(sentences),
            chunk_index=index,
            metadata={
                "strategy": self.strategy_name,
                "sentence_count": len(sentences),
                "max_chunk_size": self.max_chunk_size,
            },
        )
