"""
Análise estatística de texto extraído de documentos.

Função pura que recebe texto bruto e retorna contagens úteis
para o dashboard de corpus stats.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_BOUNDARY = re.compile(r"[.!?]+(?:\s|$)")
_PHRASE_DELIMITERS = re.compile(r"[.!?,;:\n]+")


@dataclass(frozen=True, slots=True)
class TextStats:
    word_count: int
    unique_word_count: int
    sentence_count: int
    phrase_count: int
    char_count: int


def compute_text_stats(text: str) -> TextStats:
    """Calcula estatísticas textuais a partir do texto extraído de um documento."""
    if not text or not text.strip():
        return TextStats(
            word_count=0,
            unique_word_count=0,
            sentence_count=0,
            phrase_count=0,
            char_count=0,
        )

    words = text.split()
    word_count = len(words)
    unique_word_count = len({w.lower() for w in words})

    sentence_count = len(_SENTENCE_BOUNDARY.findall(text))
    if sentence_count == 0 and word_count > 0:
        sentence_count = 1

    phrases = [p.strip() for p in _PHRASE_DELIMITERS.split(text) if p.strip()]
    phrase_count = len(phrases)

    return TextStats(
        word_count=word_count,
        unique_word_count=unique_word_count,
        sentence_count=sentence_count,
        phrase_count=phrase_count,
        char_count=len(text),
    )
