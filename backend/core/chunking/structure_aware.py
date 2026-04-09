"""
StructureAwareChunker
=====================
Estratégia especializada para Currículos Lattes (CNPq) em XML ou JSON.

Em vez de dividir por caracteres ou sentenças, respeita a estrutura hierárquica
do documento: cada produção científica (artigo, livro, capítulo, patente, etc.)
vira um chunk independente; seções de dados pessoais e formação são agrupadas.

Formatos suportados:
    - JSON (xmltodict): detectado quando o texto começa com '{' e contém
      a chave 'CURRICULO-VITAE'.
    - XML (CNPq original): detectado pela tag raiz CURRICULO-VITAE.

Para documentos que não são Lattes em nenhum dos formatos, faz fallback
automático para RecursiveCharacterChunker.

Seções mapeadas:
    DADOS-GERAIS                  → 1 chunk (dados pessoais + área de atuação)
    FORMACAO-ACADEMICA-TITULACAO  → 1 chunk por grau (grad/mestrado/doutorado/PD)
    ATUACOES-PROFISSIONAIS        → 1 chunk por vínculo institucional
    ARTIGOS-PUBLICADOS            → 1 chunk por artigo
    ARTIGOS-ACEITOS               → 1 chunk por artigo
    LIVROS-PUBLICADOS-OU-ORGANIZADOS → 1 chunk por livro
    CAPITULOS-DE-LIVROS-PUBLICADOS   → 1 chunk por capítulo
    TRABALHOS-EM-EVENTOS          → 1 chunk por trabalho
    SOFTWARE                      → 1 chunk por item
    PATENTE                       → 1 chunk por item
    ORIENTACOES-*                 → 1 chunk por orientação concluída
"""
from __future__ import annotations

import json as _json
import re
from typing import Any

from lxml import etree

from core.chunking.base import BaseChunker, ChunkData
from core.chunking.registry import register
from models.enums import ChunkingStrategy

# Tags de itens individuais que geram um chunk cada
_ITEM_TAGS: frozenset[str] = frozenset({
    "ARTIGO-PUBLICADO",
    "ARTIGO-ACEITO-PARA-PUBLICACAO",
    "LIVRO-PUBLICADO-OU-ORGANIZADO",
    "CAPITULO-DE-LIVRO-PUBLICADO",
    "TEXTO-EM-JORNAL-OU-REVISTA",
    "TRABALHO-EM-EVENTOS",
    "APRESENTACAO-DE-TRABALHO",
    "SOFTWARE",
    "PATENTE",
    "MARCA",
    "PRODUTO-TECNOLOGICO",
    "PROCESSO-OU-TECNICA",
    "ORIENTACOES-CONCLUIDAS-PARA-MESTRADO",
    "ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO",
    "ORIENTACOES-CONCLUIDAS-PARA-POS-DOUTORADO",
    "OUTRAS-ORIENTACOES-CONCLUIDAS",
    "ORIENTACAO-EM-ANDAMENTO-DE-MESTRADO",
    "ORIENTACAO-EM-ANDAMENTO-DE-DOUTORADO",
})

# Tags de seções que são agrupadas num único chunk
_SECTION_TAGS: frozenset[str] = frozenset({
    "DADOS-GERAIS",
    "DADOS-COMPLEMENTARES",
    "FORMACAO-ACADEMICA-TITULACAO",
    "ATUACOES-PROFISSIONAIS",
    "IDIOMAS",
    "PREMIOS-E-TITULOS",
    "AREAS-DE-ATUACAO",
})

# Atributos a omitir na serialização (metadados técnicos sem valor semântico)
_SKIP_ATTR_PREFIXES: tuple[str, ...] = (
    "SEQUENCIA",
    "FLAG-",
    "CODIGO-",
    "HOME-PAGE",
    "TEXTO-",
    "NATUREZA",  # codigos internos
)


def _tag_to_label(tag: str) -> str:
    """Converte tag XML em rótulo legível: 'ARTIGO-PUBLICADO' → 'Artigo Publicado'."""
    return tag.replace("-", " ").title()


def _attr_to_label(attr: str) -> str:
    """Converte nome de atributo: 'NOME-COMPLETO' → 'Nome Completo'."""
    return attr.replace("-", " ").title()


def _is_relevant_attr(name: str, value: str) -> bool:
    """Filtra atributos sem valor semântico."""
    if not value or not value.strip():
        return False
    if any(name.startswith(p) for p in _SKIP_ATTR_PREFIXES):
        return False
    # Ignora campos numéricos internos (ex: CODIGO-AREA="0300600")
    if re.fullmatch(r"\d+", value.strip()):
        return False
    return True


def _serialize_element(element: etree._Element, depth: int = 0) -> str:
    """
    Serializa recursivamente um elemento XML em texto legível.

    Cada atributo relevante vira uma linha "Rótulo: Valor".
    Elementos filhos são indentados levemente.
    """
    lines: list[str] = []
    tag_label = _tag_to_label(element.tag)

    if depth == 0:
        lines.append(f"=== {tag_label} ===")
    else:
        lines.append(f"[{tag_label}]")

    # Atributos do elemento atual
    for attr, value in element.attrib.items():
        if _is_relevant_attr(attr, value):
            lines.append(f"  {_attr_to_label(attr)}: {value.strip()}")

    # Texto direto do elemento (raro no Lattes, mas pode ocorrer)
    if element.text and element.text.strip():
        lines.append(f"  {element.text.strip()}")

    # Filhos recursivamente (apenas 1 nível de profundidade além do item)
    for child in element:
        child_lines = _serialize_element(child, depth + 1)
        if child_lines:
            lines.append(child_lines)

    return "\n".join(line for line in lines if line.strip())


def _extract_items(root: etree._Element) -> list[tuple[str, str, etree._Element]]:
    """
    Percorre toda a árvore XML e coleta itens e seções para chunking.

    Retorna lista de (section_type, tag_label, element).
    """
    items: list[tuple[str, str, etree._Element]] = []

    def walk(element: etree._Element) -> None:
        tag = element.tag
        if tag in _ITEM_TAGS:
            items.append((tag, _tag_to_label(tag), element))
        elif tag in _SECTION_TAGS:
            items.append((tag, _tag_to_label(tag), element))
        else:
            for child in element:
                walk(child)

    walk(root)
    return items


@register(ChunkingStrategy.structure_aware)
class StructureAwareChunker(BaseChunker):
    """
    Chunker especializado para Currículo Lattes (XML CNPq).

    Cada unidade de produção científica (artigo, livro, patente, etc.)
    é preservada como um chunk independente, mantendo toda a sua metainformação
    estrutural (título, ano, periódico, autores, etc.) em texto legível.

    Parâmetros:
        max_chunk_size: limite máximo de caracteres por chunk.
                        Seções longas são subdivididas.
                        Padrão: 1024 (maior que os outros chunkers, pois cada
                        item de produção pode ser verboso).
        fallback_chunk_size: chunk_size para o fallback recursivo (não-XML).
        fallback_overlap:    chunk_overlap para o fallback recursivo.

    Vantagens  : melhor preservação do contexto de cada publicação;
                 diferencial acadêmico do experimento.
    Desvantagens: exclusivo para XML Lattes; não aplicável a PDFs.
    """

    def __init__(
        self,
        max_chunk_size: int = 1024,
        fallback_chunk_size: int = 512,
        fallback_overlap: int = 50,
    ) -> None:
        self.max_chunk_size = max_chunk_size
        self.fallback_chunk_size = fallback_chunk_size
        self.fallback_overlap = fallback_overlap

    @property
    def strategy_name(self) -> str:
        return ChunkingStrategy.structure_aware.value

    def split(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        # Tenta parsear como JSON Lattes (exportado via xmltodict)
        json_data = _try_parse_json(text)
        if json_data is not None and _is_lattes_json(json_data):
            return self._split_json(json_data)

        # Tenta parsear como XML Lattes (formato original CNPq)
        root = _try_parse_xml(text)
        if root is not None and _is_lattes(root):
            return self._split_xml(root)

        # Fallback: nem JSON nem XML Lattes → usa RecursiveCharacterChunker
        return self._fallback_split(text)

    def _split_json(self, data: dict) -> list[ChunkData]:
        cv = data.get("CURRICULO-VITAE", {})
        items = _extract_items_json(cv)
        if not items:
            return self._fallback_split(_json.dumps(data, ensure_ascii=False))

        chunks: list[ChunkData] = []
        for section_type, label, item_dict in items:
            content = _serialize_json_item(section_type, item_dict).strip()
            if not content:
                continue

            base_meta: dict[str, Any] = {
                "strategy": self.strategy_name,
                "source_format": "json_lattes",
                "section_type": section_type,
                "section_label": label,
            }
            _enrich_metadata_json(item_dict, base_meta)

            if len(content) <= self.max_chunk_size:
                chunks.append(ChunkData(
                    content=content,
                    chunk_index=len(chunks),
                    metadata=base_meta,
                ))
            else:
                for j, sub in enumerate(_split_by_size(content, self.max_chunk_size)):
                    chunks.append(ChunkData(
                        content=sub,
                        chunk_index=len(chunks),
                        metadata={**base_meta, "sub_index": j},
                    ))

        return chunks

    def _split_xml(self, root: etree._Element) -> list[ChunkData]:
        items = _extract_items(root)
        if not items:
            # XML Lattes vazio ou estrutura desconhecida
            return self._fallback_split(etree.tostring(root, encoding="unicode"))

        chunks: list[ChunkData] = []

        for section_type, label, element in items:
            content = _serialize_element(element)
            content = content.strip()

            if not content:
                continue

            base_meta: dict[str, Any] = {
                "strategy": self.strategy_name,
                "source_format": "xml_lattes",
                "section_type": section_type,
                "section_label": label,
            }

            # Enriquece metadados com atributos-chave do elemento
            _enrich_metadata(element, base_meta)

            if len(content) <= self.max_chunk_size:
                chunks.append(
                    ChunkData(
                        content=content,
                        chunk_index=len(chunks),
                        metadata=base_meta,
                    )
                )
            else:
                # Subdivisão por tamanho para seções muito longas
                for j, sub in enumerate(_split_by_size(content, self.max_chunk_size)):
                    chunks.append(
                        ChunkData(
                            content=sub,
                            chunk_index=len(chunks),
                            metadata={**base_meta, "sub_index": j},
                        )
                    )

        return chunks

    def _fallback_split(self, text: str) -> list[ChunkData]:
        from core.chunking.recursive import RecursiveCharacterChunker  # noqa: PLC0415

        fallback = RecursiveCharacterChunker(
            chunk_size=self.fallback_chunk_size,
            chunk_overlap=self.fallback_overlap,
        )
        chunks = fallback.split(text)

        # Marca que veio do fallback e atualiza strategy nos metadados
        for chunk in chunks:
            chunk.metadata["strategy"] = self.strategy_name
            chunk.metadata["fallback"] = True
            chunk.metadata["source_format"] = "plain_text"

        return chunks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _try_parse_xml(text: str) -> etree._Element | None:
    """Tenta parsear o texto como XML. Retorna None se falhar."""
    try:
        return etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError:
        return None


def _is_lattes(root: etree._Element) -> bool:
    """Verifica se o XML é um Currículo Lattes."""
    return root.tag == "CURRICULO-VITAE"


def _enrich_metadata(element: etree._Element, meta: dict[str, Any]) -> None:
    """
    Adiciona ao dict de metadados os atributos mais úteis para rastreabilidade
    (título, ano, periódico) se existirem no elemento ou nos seus filhos diretos.
    """
    key_attrs = {"TITULO", "ANO", "NOME-DO-PERIODICO", "NOME-COMPLETO", "INSTITUICAO"}
    found: dict[str, str] = {}

    for attr, value in element.attrib.items():
        if attr in key_attrs and value.strip():
            found[attr.lower().replace("-", "_")] = value.strip()

    for child in element:
        for attr, value in child.attrib.items():
            if attr in key_attrs and attr.lower().replace("-", "_") not in found:
                if value.strip():
                    found[attr.lower().replace("-", "_")] = value.strip()

    meta.update(found)


def _split_by_size(text: str, max_size: int) -> list[str]:
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


# ── JSON Lattes helpers ────────────────────────────────────────────────────────

def _try_parse_json(text: str) -> dict | None:
    """Tenta parsear o texto como JSON. Retorna None se falhar ou não for dict."""
    if not text.strip().startswith("{"):
        return None
    try:
        data = _json.loads(text)
        return data if isinstance(data, dict) else None
    except (ValueError, _json.JSONDecodeError):
        return None


def _is_lattes_json(data: dict) -> bool:
    """Verifica se o JSON é um Currículo Lattes."""
    return "CURRICULO-VITAE" in data


_JSON_SKIP_ATTR_PREFIXES: tuple[str, ...] = (
    "@SEQUENCIA",
    "@FLAG-",
    "@CODIGO-",
    "@HOME-PAGE",
    "@TEXTO-",
    "@NATUREZA",
    "@SIGLA-",
)

_JSON_ITEM_LABELS: dict[str, str] = {
    "DADOS-GERAIS": "Dados Gerais",
    "DADOS-COMPLEMENTARES": "Dados Complementares",
    "ARTIGO-PUBLICADO": "Artigo Publicado",
    "ARTIGO-ACEITO-PARA-PUBLICACAO": "Artigo Aceito para Publicação",
    "LIVRO-PUBLICADO-OU-ORGANIZADO": "Livro Publicado ou Organizado",
    "CAPITULO-DE-LIVRO-PUBLICADO": "Capítulo de Livro",
    "TRABALHO-EM-EVENTOS": "Trabalho em Eventos",
    "SOFTWARE": "Software",
    "PATENTE": "Patente",
    "ORIENTACOES-CONCLUIDAS-PARA-MESTRADO": "Orientação Concluída de Mestrado",
    "ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO": "Orientação Concluída de Doutorado",
    "ORIENTACAO-EM-ANDAMENTO-DE-MESTRADO": "Orientação em Andamento de Mestrado",
    "ORIENTACAO-EM-ANDAMENTO-DE-DOUTORADO": "Orientação em Andamento de Doutorado",
    "OUTRAS-ORIENTACOES-CONCLUIDAS": "Outras Orientações Concluídas",
    "ORIENTACOES-CONCLUIDAS-PARA-POS-DOUTORADO": "Orientação Concluída de Pós-Doutorado",
}


def _is_relevant_json_attr(key: str, value: Any) -> bool:
    """Filtra atributos sem valor semântico no formato JSON Lattes."""
    if not key.startswith("@"):
        return False
    if not value or (isinstance(value, str) and not value.strip()):
        return False
    if any(key.startswith(p) for p in _JSON_SKIP_ATTR_PREFIXES):
        return False
    if isinstance(value, str) and value.strip().isdigit():
        return False
    return True


def _attr_label_json(key: str) -> str:
    """'@TITULO-DO-ARTIGO' → 'Titulo Do Artigo'."""
    return key.lstrip("@").replace("-", " ").title()


def _serialize_json_item(section_type: str, item: dict[str, Any]) -> str:
    """Serializa um item JSON de Lattes em texto legível (recursivo)."""
    label = _JSON_ITEM_LABELS.get(section_type, section_type.replace("-", " ").title())
    lines: list[str] = [f"=== {label} ==="]
    _walk_json(item, lines, depth=0)
    return "\n".join(line for line in lines if line.strip())


def _walk_json(node: Any, lines: list[str], depth: int) -> None:
    """
    Percorre recursivamente um nó JSON adicionando linhas de texto legível.

    - Atributos @-prefixados relevantes → "  Attr Label: valor"
    - Chaves sem @ com valor dict/list → "[Sub Label]" + recursão
    - Profundidade máxima: 5 (evita loops em estruturas inesperadas)
    """
    if depth > 5:
        return
    pad = "  " * depth

    if isinstance(node, dict):
        for key, val in node.items():
            if _is_relevant_json_attr(key, val):
                lines.append(f"{pad}  {_attr_label_json(key)}: {str(val).strip()}")
            elif not key.startswith("@") and isinstance(val, (dict, list)):
                sub_label = key.replace("-", " ").title()
                lines.append(f"{pad}[{sub_label}]")
                _walk_json(val, lines, depth + 1)
    elif isinstance(node, list):
        for item in node:
            _walk_json(item, lines, depth)


def _enrich_metadata_json(item: dict[str, Any], meta: dict[str, Any]) -> None:
    """
    Adiciona ao dict de metadados os atributos-chave do item JSON
    (título, ano, periódico) para rastreabilidade.
    """
    _key_attrs = {
        "@TITULO-DO-ARTIGO", "@ANO-DO-ARTIGO",
        "@TITULO-DO-PERIODICO-OU-REVISTA",
        "@TITULO-DO-TRABALHO", "@ANO-DO-TRABALHO",
        "@NOME-COMPLETO", "@TITULO", "@ANO",
    }

    def walk(d: dict) -> None:
        for k, v in d.items():
            if k in _key_attrs and v and str(v).strip():
                meta_key = k.lstrip("@").lower().replace("-", "_")
                if meta_key not in meta:
                    meta[meta_key] = str(v).strip()
            elif isinstance(v, dict):
                walk(v)

    walk(item)


def _ensure_list_json(val: Any) -> list:
    """Garante lista (xmltodict retorna dict para itens únicos)."""
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


def _extract_items_json(cv: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Extrai itens e seções do currículo Lattes em JSON para chunking.

    Retorna lista de (section_type, section_label, item_dict).
    """
    items: list[tuple[str, str, dict[str, Any]]] = []

    # Seções agrupadas (1 chunk por seção)
    for section_key in ("DADOS-GERAIS", "DADOS-COMPLEMENTARES"):
        section = cv.get(section_key)
        if section and isinstance(section, dict):
            label = _JSON_ITEM_LABELS.get(section_key, section_key.replace("-", " ").title())
            items.append((section_key, label, section))

    # Produção bibliográfica (1 chunk por item)
    prod_bib = cv.get("PRODUCAO-BIBLIOGRAFICA") or {}
    _collect_json_items(prod_bib, "ARTIGOS-PUBLICADOS", "ARTIGO-PUBLICADO", items)
    _collect_json_items(prod_bib, "ARTIGOS-ACEITOS", "ARTIGO-ACEITO-PARA-PUBLICACAO", items)
    _collect_json_items(prod_bib, "LIVROS-PUBLICADOS-OU-ORGANIZADOS", "LIVRO-PUBLICADO-OU-ORGANIZADO", items)
    _collect_json_items(prod_bib, "CAPITULOS-DE-LIVROS-PUBLICADOS", "CAPITULO-DE-LIVRO-PUBLICADO", items)
    _collect_json_items(prod_bib, "TRABALHOS-EM-EVENTOS", "TRABALHO-EM-EVENTOS", items)

    # Produção técnica
    prod_tec = cv.get("PRODUCAO-TECNICA") or {}
    _collect_json_items(prod_tec, "SOFTWARE", "SOFTWARE", items)
    _collect_json_items(prod_tec, "PATENTE", "PATENTE", items)

    # Outra produção — orientações ficam aqui em muitos currículos
    outra_prod = cv.get("OUTRA-PRODUCAO") or {}
    _collect_json_items_flat(
        outra_prod, "ORIENTACOES-CONCLUIDAS",
        (
            "OUTRAS-ORIENTACOES-CONCLUIDAS",
            "ORIENTACOES-CONCLUIDAS-PARA-MESTRADO",
            "ORIENTACOES-CONCLUIDAS-PARA-DOUTORADO",
            "ORIENTACOES-CONCLUIDAS-PARA-POS-DOUTORADO",
        ),
        items,
    )

    return items


def _collect_json_items(
    parent: dict[str, Any],
    section_key: str,
    item_key: str,
    items: list[tuple[str, str, dict[str, Any]]],
) -> None:
    """
    Coleta itens individuais de parent[section_key][item_key].

    Estrutura esperada: parent → {section_key: {item_key: dict | list}}
    """
    section = parent.get(section_key)
    if not section or not isinstance(section, dict):
        return
    raw_items = _ensure_list_json(section.get(item_key))
    label = _JSON_ITEM_LABELS.get(item_key, item_key.replace("-", " ").title())
    for item in raw_items:
        if isinstance(item, dict):
            items.append((item_key, label, item))


def _collect_json_items_flat(
    parent: dict[str, Any],
    section_key: str,
    item_keys: tuple[str, ...],
    items: list[tuple[str, str, dict[str, Any]]],
) -> None:
    """
    Coleta múltiplos tipos de itens de parent[section_key].

    Usado para seções onde os itens de diferentes tipos estão lado a lado:
        parent → {section_key: {item_key_1: list, item_key_2: list, ...}}

    Exemplo: OUTRA-PRODUCAO.ORIENTACOES-CONCLUIDAS.OUTRAS-ORIENTACOES-CONCLUIDAS
    """
    section = parent.get(section_key)
    if not section or not isinstance(section, dict):
        return
    for item_key in item_keys:
        raw_items = _ensure_list_json(section.get(item_key))
        label = _JSON_ITEM_LABELS.get(item_key, item_key.replace("-", " ").title())
        for item in raw_items:
            if isinstance(item, dict):
                items.append((item_key, label, item))
