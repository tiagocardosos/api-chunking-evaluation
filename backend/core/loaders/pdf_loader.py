"""
PDFLoader
=========
Extrai texto de PDFs usando PyMuPDF (fitz).

Particularidades dos PDFs brasileiros institucionais (editais EMBRAPII, etc.):
    - Encoding variado (às vezes Latin-1 embutido)
    - Hifenização no fim de linhas (tratada via post-processing)
    - Cabeçalhos/rodapés repetidos em cada página (não removidos aqui,
      pois podem conter informações relevantes para busca)
    - Páginas em branco ou apenas com imagens (ignoradas automaticamente)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class PDFPage:
    page_number: int       # 1-indexed
    text: str
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class PDFDocument:
    filename: str
    total_pages: int
    pages: list[PDFPage]
    full_text: str = field(init=False)

    def __post_init__(self) -> None:
        self.full_text = "\n\n".join(p.text for p in self.pages if p.text.strip())


def load_pdf(source: bytes | str | Path) -> PDFDocument:
    """
    Carrega um PDF a partir de bytes, caminho de arquivo ou Path.

    Args:
        source: conteúdo binário do PDF, ou caminho para o arquivo.

    Returns:
        PDFDocument com texto por página e full_text concatenado.

    Raises:
        ValueError: se o PDF não puder ser aberto ou estiver corrompido.
    """
    try:
        if isinstance(source, bytes):
            doc = fitz.open(stream=source, filetype="pdf")
            filename = "upload.pdf"
        else:
            path = Path(source)
            doc = fitz.open(str(path))
            filename = path.name
    except Exception as exc:
        raise ValueError(f"Não foi possível abrir o PDF: {exc}") from exc

    pages: list[PDFPage] = []

    with doc:
        total_pages = doc.page_count  # captura antes de fechar o documento
        for i, page in enumerate(doc):
            raw_text = page.get_text("text")
            cleaned = _clean_pdf_text(raw_text)
            if cleaned.strip():
                pages.append(PDFPage(page_number=i + 1, text=cleaned))

    if not pages:
        raise ValueError(
            f"PDF '{filename}' não contém texto extraível "
            f"({total_pages} página(s) processada(s)). "
            "O arquivo pode ser baseado em imagens — use um PDF com camada de texto."
        )

    return PDFDocument(filename=filename, total_pages=total_pages, pages=pages)


def _clean_pdf_text(text: str) -> str:
    """
    Pós-processamento do texto extraído do PDF:
        1. Remove hifenização de fim de linha (palavra- \\n palavra → palavra palavra).
        2. Colapsa espaços múltiplos.
        3. Preserva quebras de parágrafo (linhas em branco).
    """
    import re

    # Remove hifenização: "pala-\nvra" → "palavra"
    text = re.sub(r"-\n(\w)", r"\1", text)

    # Colapsa quebras de linha simples em espaço (mantém parágrafos com \n\n)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Remove espaços múltiplos
    text = re.sub(r" {2,}", " ", text)

    return text.strip()
