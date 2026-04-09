"""
JSONLattesLoader
================
Carrega currículos Lattes no formato JSON (convertidos via xmltodict).

Particularidades do formato:
    - Atributos XML são prefixados com '@' (ex: '@NOME-COMPLETO').
    - Único item numa seção pode ser dict; múltiplos são list.
      → _ensure_list() converte ambos os casos para list.
    - Estrutura top-level: {"CURRICULO-VITAE": {...}, "id": ..., ...}
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LattesJsonDocument:
    filename: str
    raw_content: str        # JSON original (string) — para StructureAwareChunker
    plain_text: str         # Texto legível — para chunkers genéricos
    researcher_name: str    # Nome do pesquisador (para logging/metadados)


def load_json_lattes(source: bytes | str | Path) -> LattesJsonDocument:
    """
    Carrega um currículo Lattes em formato JSON.

    Args:
        source: bytes do arquivo, string JSON, ou caminho para o arquivo.

    Returns:
        LattesJsonDocument com raw_content e plain_text.

    Raises:
        ValueError: se o JSON não for um currículo Lattes válido.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        raw_bytes = path.read_bytes()
        filename = path.name
    else:
        raw_bytes = source
        filename = "upload.json"

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    if not isinstance(data, dict) or "CURRICULO-VITAE" not in data:
        raise ValueError(
            "JSON não contém chave 'CURRICULO-VITAE'. "
            "Verifique se o arquivo é um currículo Lattes exportado via xmltodict."
        )

    cv = data["CURRICULO-VITAE"]
    dados_gerais = cv.get("DADOS-GERAIS", {})
    researcher_name = dados_gerais.get("@NOME-COMPLETO", "Desconhecido")

    plain_text = _extract_plain_text(cv)
    raw_content = raw_bytes.decode("utf-8")

    return LattesJsonDocument(
        filename=filename,
        raw_content=raw_content,
        plain_text=plain_text,
        researcher_name=researcher_name,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_list(val: Any) -> list:
    """Garante que val seja uma lista (xmltodict retorna dict para itens únicos)."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


_SKIP_ATTR_PREFIXES: tuple[str, ...] = (
    "@SEQUENCIA",
    "@FLAG-",
    "@CODIGO-",
    "@HOME-PAGE",
    "@TEXTO-",
    "@SIGLA-",
    "@NATUREZA",
)

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


def _is_relevant_attr(key: str, value: Any) -> bool:
    """Filtra atributos sem valor semântico."""
    if not key.startswith("@"):
        return False
    if not value or (isinstance(value, str) and not value.strip()):
        return False
    if any(key.startswith(p) for p in _SKIP_ATTR_PREFIXES):
        return False
    # Ignora valores puramente numéricos (códigos internos)
    if isinstance(value, str) and value.strip().isdigit():
        return False
    return True


def _attr_to_label(key: str) -> str:
    """'@NOME-COMPLETO' → 'Nome Completo'."""
    return key.lstrip("@").replace("-", " ").title()


def _extract_plain_text(cv: dict) -> str:
    """
    Extrai texto legível do currículo Lattes em JSON para chunkers genéricos
    (fixed_size, recursive, sentence, semantic).
    """
    sections: list[str] = []

    # Dados Gerais + Formação Acadêmica
    dg = cv.get("DADOS-GERAIS", {})
    if dg:
        lines: list[str] = ["** Dados Pessoais **"]
        for k, v in dg.items():
            if _is_relevant_attr(k, v):
                lines.append(f"  {_attr_to_label(k)}: {str(v).strip()}")
        # Formação acadêmica fica dentro de DADOS-GERAIS
        form = dg.get("FORMACAO-ACADEMICA-TITULACAO", {})
        if isinstance(form, dict):
            for grau, items in form.items():
                grau_label = _SECTION_LABELS.get(grau, grau.replace("-", " ").title())
                for item in _ensure_list(items):
                    if not isinstance(item, dict):
                        continue
                    lines.append(f"** {grau_label} **")
                    for k2, v2 in item.items():
                        if _is_relevant_attr(k2, v2):
                            lines.append(f"  {_attr_to_label(k2)}: {str(v2).strip()}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    # Produção Bibliográfica
    prod_bib = cv.get("PRODUCAO-BIBLIOGRAFICA") or {}
    _collect_section(prod_bib, "ARTIGOS-PUBLICADOS", "ARTIGO-PUBLICADO", sections)
    _collect_section(prod_bib, "ARTIGOS-ACEITOS", "ARTIGO-ACEITO-PARA-PUBLICACAO", sections)
    _collect_section(prod_bib, "TRABALHOS-EM-EVENTOS", "TRABALHO-EM-EVENTOS", sections)
    _collect_section(prod_bib, "LIVROS-PUBLICADOS-OU-ORGANIZADOS", "LIVRO-PUBLICADO-OU-ORGANIZADO", sections)
    _collect_section(prod_bib, "CAPITULOS-DE-LIVROS-PUBLICADOS", "CAPITULO-DE-LIVRO-PUBLICADO", sections)

    # Produção Técnica
    prod_tec = cv.get("PRODUCAO-TECNICA") or {}
    _collect_section(prod_tec, "SOFTWARE", "SOFTWARE", sections)
    _collect_section(prod_tec, "PATENTE", "PATENTE", sections)

    # Dados Complementares
    dc = cv.get("DADOS-COMPLEMENTARES") or {}
    if dc:
        lines = ["** Dados Complementares **"]
        for k, v in dc.items():
            if _is_relevant_attr(k, v):
                lines.append(f"  {_attr_to_label(k)}: {str(v).strip()}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    return "\n\n".join(s for s in sections if s.strip())


def _collect_section(
    parent: dict,
    section_key: str,
    item_key: str,
    sections: list[str],
) -> None:
    """Serializa itens de uma seção em texto legível e acrescenta a sections."""
    section = parent.get(section_key) or {}
    if not isinstance(section, dict):
        return
    raw_items = _ensure_list(section.get(item_key))
    label = _SECTION_LABELS.get(item_key, item_key.replace("-", " ").title())

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        lines: list[str] = [f"** {label} **"]
        for key, val in item.items():
            if isinstance(val, dict):
                sub_label = key.replace("-", " ").title()
                lines.append(f"[{sub_label}]")
                for k2, v2 in val.items():
                    if _is_relevant_attr(k2, v2):
                        lines.append(f"  {_attr_to_label(k2)}: {str(v2).strip()}")
            elif isinstance(val, list):
                sub_label = key.replace("-", " ").title()
                lines.append(f"[{sub_label}]")
                for sub_item in val:
                    if isinstance(sub_item, dict):
                        for k2, v2 in sub_item.items():
                            if _is_relevant_attr(k2, v2):
                                lines.append(f"  {_attr_to_label(k2)}: {str(v2).strip()}")
            elif _is_relevant_attr(key, val):
                lines.append(f"  {_attr_to_label(key)}: {str(val).strip()}")
        if len(lines) > 1:
            sections.append("\n".join(lines))
