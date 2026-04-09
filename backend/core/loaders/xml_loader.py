"""
XMLLattesLoader
===============
Carrega XMLs de Currículo Lattes (CNPq).

Modos de uso:
    - raw_xml  : retorna a string XML completa (para StructureAwareChunker).
    - plain_text: extrai texto legível dos atributos XML (para outros chunkers).

Tratamento de encoding:
    Lattes exporta em ISO-8859-1. O loader detecta o encoding declarado no
    cabeçalho XML e converte para UTF-8 antes de processar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree


@dataclass
class LattesDocument:
    filename: str
    raw_xml: str            # XML original em UTF-8
    plain_text: str         # Texto extraído dos atributos para chunkers genéricos
    researcher_name: str    # NOME-COMPLETO de DADOS-GERAIS (para logging/metadados)


def load_xml(source: bytes | str | Path) -> LattesDocument:
    """
    Carrega um XML Lattes a partir de bytes, string ou caminho.

    Args:
        source: conteúdo binário/textual do XML ou caminho para o arquivo.

    Returns:
        LattesDocument com raw_xml e plain_text.

    Raises:
        ValueError: se não for um XML Lattes válido.
    """
    if isinstance(source, bytes):
        raw_bytes = source
        filename = "upload.xml"
    else:
        path = Path(source)
        raw_bytes = path.read_bytes()
        filename = path.name

    # Detecta e normaliza encoding
    xml_str = _normalize_encoding(raw_bytes)

    # Parseia para validar estrutura
    try:
        root = etree.fromstring(xml_str.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"XML inválido: {exc}") from exc

    if root.tag != "CURRICULO-VITAE":
        raise ValueError(
            f"Esperado CURRICULO-VITAE como tag raiz, encontrado: {root.tag!r}"
        )

    researcher_name = root.find(".//DADOS-GERAIS")
    name = (
        researcher_name.get("NOME-COMPLETO", "Desconhecido")
        if researcher_name is not None
        else "Desconhecido"
    )

    plain_text = _extract_plain_text(root)

    return LattesDocument(
        filename=filename,
        raw_xml=xml_str,
        plain_text=plain_text,
        researcher_name=name,
    )


def _normalize_encoding(raw_bytes: bytes) -> str:
    """
    Detecta o encoding declarado no XML e converte para UTF-8.
    Lattes usa ISO-8859-1; outros sistemas podem usar UTF-8.
    """
    # Tenta detectar encoding no cabeçalho XML
    header = raw_bytes[:200].decode("ascii", errors="replace")
    match = re.search(r'encoding=["\']([^"\']+)["\']', header, re.IGNORECASE)

    if match:
        declared_encoding = match.group(1).upper()
    else:
        declared_encoding = "UTF-8"

    # Decodifica com o encoding declarado
    try:
        text = raw_bytes.decode(declared_encoding)
    except (UnicodeDecodeError, LookupError):
        # Fallback: tenta UTF-8, depois Latin-1
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1")

    # Remove declaração de encoding para evitar conflito ao re-parsear como UTF-8
    text = re.sub(
        r'<\?xml[^?]*encoding=["\'][^"\']*["\'][^?]*\?>',
        '<?xml version="1.0" encoding="UTF-8"?>',
        text,
        count=1,
    )

    return text


def _extract_plain_text(root: etree._Element) -> str:
    """
    Extrai texto legível do XML Lattes para chunkers genéricos
    (fixed_size, recursive, sentence, semantic).

    Estratégia: percorre todos os atributos com valor textual (não-numérico)
    e os organiza em seções legíveis.
    """
    sections: list[str] = []
    _walk_element(root, sections, depth=0)
    return "\n\n".join(s for s in sections if s.strip())


_SKIP_ATTRS: frozenset[str] = frozenset({
    "SEQUENCIA", "CODIGO-AREA", "FLAG-RELEVANCIA",
    "HOME-PAGE", "E-MAIL", "SIGLA-",
})

_SECTION_LABELS: dict[str, str] = {
    "DADOS-GERAIS": "Dados Pessoais",
    "FORMACAO-ACADEMICA-TITULACAO": "Formação Acadêmica",
    "ATUACOES-PROFISSIONAIS": "Atuações Profissionais",
    "ARTIGO-PUBLICADO": "Artigo Publicado",
    "ARTIGO-ACEITO-PARA-PUBLICACAO": "Artigo Aceito",
    "LIVRO-PUBLICADO-OU-ORGANIZADO": "Livro Publicado",
    "CAPITULO-DE-LIVRO-PUBLICADO": "Capítulo de Livro",
    "TRABALHO-EM-EVENTOS": "Trabalho em Evento",
    "SOFTWARE": "Software",
    "PATENTE": "Patente",
    "DOUTORADO": "Doutorado",
    "MESTRADO": "Mestrado",
    "GRADUACAO": "Graduação",
    "POS-DOUTORADO": "Pós-Doutorado",
    "ORIENTACOES-CONCLUIDAS-PARA-MESTRADO": "Orientação de Mestrado",
    "ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO": "Orientação de Doutorado",
}


def _walk_element(element: etree._Element, sections: list[str], depth: int) -> None:
    tag = element.tag
    label = _SECTION_LABELS.get(tag)

    lines: list[str] = []
    if label:
        lines.append(f"** {label} **")

    for attr, value in element.attrib.items():
        if not value or not value.strip():
            continue
        if any(attr.startswith(s) for s in _SKIP_ATTRS):
            continue
        readable_attr = attr.replace("-", " ").title()
        lines.append(f"{readable_attr}: {value.strip()}")

    if len(lines) > (1 if label else 0):
        sections.append("\n".join(lines))

    for child in element:
        _walk_element(child, sections, depth + 1)
