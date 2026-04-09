"""
GoldenSetLoader
===============
Carrega e valida o golden set de 180 perguntas (EXPERIMENT-SPEC §4).

Formato esperado do JSON:
    [
      {
        "question":        "Qual o prazo máximo de execução de projetos EMBRAPII?",
        "expected_answer": "24 meses.",
        "question_type":   "factual",      // factual | inferential
        "doc_type":        "pdf",          // pdf | xml_lattes
        "source_doc":      "edital_2023.pdf"  // opcional, para rastreabilidade
      },
      ...
    ]

Distribuição esperada (EXPERIMENT-SPEC §4):
    - 180 perguntas total
    - 90 factual/procedimental + 90 inferencial
    - Análise separada: PDF vs XML Lattes
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


QuestionType = Literal["factual", "inferential"]
DocType = Literal["pdf", "xml_lattes"]


@dataclass
class GoldenQuestion:
    question: str
    expected_answer: str | None
    question_type: QuestionType
    doc_type: DocType
    source_doc: str | None = None


class GoldenSet:
    def __init__(self, questions: list[GoldenQuestion]) -> None:
        self.questions = questions

    def __len__(self) -> int:
        return len(self.questions)

    def filter_by_type(self, question_type: QuestionType) -> "GoldenSet":
        return GoldenSet([q for q in self.questions if q.question_type == question_type])

    def filter_by_doc(self, doc_type: DocType) -> "GoldenSet":
        return GoldenSet([q for q in self.questions if q.doc_type == doc_type])

    def stats(self) -> dict:
        return {
            "total": len(self),
            "factual": sum(1 for q in self.questions if q.question_type == "factual"),
            "inferential": sum(1 for q in self.questions if q.question_type == "inferential"),
            "pdf": sum(1 for q in self.questions if q.doc_type == "pdf"),
            "xml_lattes": sum(1 for q in self.questions if q.doc_type == "xml_lattes"),
            "with_answer": sum(1 for q in self.questions if q.expected_answer),
        }


def load_golden_set(path: str | Path) -> GoldenSet:
    """
    Carrega o golden set a partir de um arquivo JSON.

    Args:
        path: caminho para o arquivo JSON.

    Returns:
        GoldenSet validado.

    Raises:
        ValueError: se o formato for inválido ou campos obrigatórios estiverem ausentes.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Golden set não encontrado: {path}")

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("O golden set deve ser uma lista JSON de objetos.")

    questions: list[GoldenQuestion] = []
    errors: list[str] = []

    for i, item in enumerate(raw):
        try:
            questions.append(_parse_question(item, i))
        except (KeyError, ValueError) as exc:
            errors.append(f"  Item {i}: {exc}")

    if errors:
        raise ValueError(
            f"Golden set contém {len(errors)} erro(s):\n" + "\n".join(errors)
        )

    gs = GoldenSet(questions)
    _warn_if_imbalanced(gs)
    return gs


def _parse_question(item: dict, index: int) -> GoldenQuestion:
    if "question" not in item:
        raise ValueError("campo obrigatório 'question' ausente")

    question_type = item.get("question_type", "factual")
    if question_type not in ("factual", "inferential"):
        raise ValueError(
            f"question_type inválido: {question_type!r} "
            "(aceito: 'factual' | 'inferential')"
        )

    doc_type = item.get("doc_type", "pdf")
    if doc_type not in ("pdf", "xml_lattes"):
        raise ValueError(
            f"doc_type inválido: {doc_type!r} (aceito: 'pdf' | 'xml_lattes')"
        )

    return GoldenQuestion(
        question=item["question"],
        expected_answer=item.get("expected_answer"),
        question_type=question_type,
        doc_type=doc_type,
        source_doc=item.get("source_doc"),
    )


def _warn_if_imbalanced(gs: GoldenSet) -> None:
    stats = gs.stats()
    # Aviso se a distribuição estiver muito desbalanceada (>60/40)
    total = stats["total"]
    if total == 0:
        return
    for key in ("factual", "inferential", "pdf", "xml_lattes"):
        ratio = stats[key] / total
        if ratio > 0.70 or ratio < 0.30:
            print(
                f"[AVISO] Golden set desbalanceado: "
                f"{stats[key]}/{total} ({ratio:.0%}) são '{key}'."
            )
