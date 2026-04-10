# Estratégias de Chunking – Detalhamento Técnico

Documento de referência das cinco estratégias implementadas em `backend/core/chunking/`, alinhado ao plano em `docs/EXPERIMENT-SPEC.md`.

## Contrato comum

- **Interface:** `BaseChunker` em `backend/core/chunking/base.py` — método `split(text: str) -> list[ChunkData]`.
- **Entrada:** texto já extraído (PDF/XML/JSON); o chunker não lê arquivos.
- **Saída:** lista ordenada de `ChunkData` com `content`, `chunk_index` e `metadata` (sempre inclui `"strategy"`).
- **Registry:** `backend/core/chunking/registry.py` — decorador `@register`, `get_chunker(ChunkingStrategy, **kwargs)`, `list_strategies()`.
- **Enum:** `ChunkingStrategy` em `backend/models/enums.py` — valores: `fixed_size`, `recursive`, `sentence`, `semantic`, `structure_aware`.

**Unidade de tamanho:** salvo indicação contrária, limites em **caracteres** (não tokens do modelo de embedding).

---

## Visão geral

| Estratégia (enum)   | Classe                    | Arquivo                 |
|---------------------|---------------------------|-------------------------|
| `fixed_size`        | `FixedSizeChunker`        | `fixed_size.py`         |
| `recursive`         | `RecursiveCharacterChunker` | `recursive.py`      |
| `sentence`          | `SentenceChunker`         | `sentence.py`           |
| `semantic`          | `SemanticChunker`         | `semantic.py`           |
| `structure_aware`   | `StructureAwareChunker`   | `structure_aware.py`    |

---

## 1. Fixed-size (`FixedSizeChunker`)

Janelas deslizantes sobre o texto: cada chunk tem até `chunk_size` caracteres; o próximo chunk começa após `chunk_size - chunk_overlap` caracteres.

**Parâmetros**

| Parâmetro        | Tipo | Descrição |
|------------------|------|-----------|
| `chunk_size`     | int  | Tamanho máximo do chunk em caracteres. |
| `chunk_overlap`  | int  | Caracteres repetidos entre chunks consecutivos. |

**Restrições:** `chunk_size > 0`, `chunk_overlap >= 0`, `chunk_overlap < chunk_size`.

**Experimento (EXPERIMENT-SPEC §3):** varrer `chunk_size ∈ {256, 512, 1024}` e `chunk_overlap ∈ {0, 50, 128}` nas combinações válidas.

**Prós / contras:** determinístico e barato; ignora fronteiras de palavra/frase.

---

## 2. Recursive character (`RecursiveCharacterChunker`)

Usa `langchain_text_splitters.RecursiveCharacterTextSplitter` com separadores priorizados para texto acadêmico em português (parágrafos, linhas, pontuação de frase, espaço, caractere). Objetivo: evitar cortes no meio de unidades maiores quando possível.

**Parâmetros**

| Parâmetro        | Tipo | Descrição |
|------------------|------|-----------|
| `chunk_size`     | int  | Teto alvo em caracteres por chunk (LangChain). |
| `chunk_overlap`  | int  | Sobreposição em caracteres entre chunks. |
| `separators`     | list[str] \| None | Opcional; default = lista em `recursive.py`. |

**Experimento:** para comparar com fixed-size de forma justa, pode-se reutilizar a mesma grade de `chunk_size` / `chunk_overlap`; alternativamente fixar um par canônico (ex.: 512 / 50) se o foco for só o tipo de algoritmo.

**Prós / contras:** melhor que fixed-size em fronteiras naturais; ainda não usa semântica profunda.

---

## 3. Sentence-based (`SentenceChunker`)

Segmenta com `split_sentences` (português: abreviações como Dr., art., etc. protegidas), agrupa sentenças até `max_chunk_size` e opcionalmente repete as últimas N sentenças no chunk seguinte.

**Parâmetros**

| Parâmetro            | Tipo | Descrição |
|----------------------|------|-----------|
| `max_chunk_size`     | int  | Limite de caracteres por chunk (buffer de sentenças). |
| `overlap_sentences`  | int  | Quantidade de sentenças de sobreposição entre chunks; `0` desliga. |

**Nota:** não há `chunk_overlap` em caracteres; o overlap é **por sentença**. Para alinhar ao experimento de tamanhos, use `max_chunk_size ∈ {256, 512, 1024}` e defina níveis de `overlap_sentences` (ex.: 0 e 1) no protocolo.

**Prós / contras:** frases inteiras; tamanho dos chunks varia.

---

## 4. Semantic (`SemanticChunker`)

Embeddings (OpenAI, alinhados ao retrieval do experimento) por sentença; similaridade cosseno entre sentenças adjacentes; quebras onde a similaridade cai abaixo de um percentil (`breakpoint_percentile`). Segmentos muito longos são truncados com fallback por caractere até `max_chunk_size`.

**Parâmetros**

| Parâmetro                 | Tipo | Descrição |
|---------------------------|------|-----------|
| `embedding_model`         | str \| None | Default: configuração da aplicação (`None` resolve no embedder). |
| `breakpoint_percentile`   | int  | Percentil em [0, 100]; menor → menos cortes (chunks tendencialmente maiores). |
| `max_chunk_size`          | int  | Teto de segurança em caracteres por chunk / sub-split. |

**Experimento:** variar principalmente `breakpoint_percentile`; `max_chunk_size` costuma alinhar a 512 ou 1024. Não há overlap clássico entre chunks.

**Prós / contras:** fronteiras temáticas; custo e latência na ingestão; comportamento pode mudar se o modelo de embedding mudar.

---

## 5. Structure-aware (`StructureAwareChunker`)

Destinado a **Currículo Lattes** em XML (raiz `CURRICULO-VITAE`) ou JSON (chave `CURRICULO-VITAE`, ex.: exportação via xmltodict). Cada item de produção ou seção mapeada vira um chunk (artigos, livros, patentes, dados gerais, etc.); conteúdo serializado como texto legível com rótulos.

**Parâmetros**

| Parâmetro               | Tipo | Descrição |
|-------------------------|------|-----------|
| `max_chunk_size`        | int  | Se item/seção exceder, subdivisão por caracteres sem overlap. |
| `fallback_chunk_size`   | int  | `chunk_size` do `RecursiveCharacterChunker` quando o texto não é Lattes. |
| `fallback_overlap`      | int  | `chunk_overlap` desse fallback. |

**PDFs / texto plano:** entra no fallback recursivo; aí `fallback_chunk_size` e `fallback_overlap` são os análogos de `chunk_size` / `chunk_overlap` das estratégias 1–2.

**Prós / contras:** preserva unidades semânticas do CV; específico para Lattes; em XML bem formado o tamanho do chunk segue a estrutura, não uma grade fixa.

---

## Grade de hiperparâmetros e combinatória

- **Fixed-size e recursive:** mesma linguagem (`chunk_size`, `chunk_overlap` em caracteres); a grade 3×3 do spec gera várias condições — avaliar se roda fatorial completo ou subconjunto (ex.: fixar overlap e variar só `chunk_size`).
- **Sentence:** `max_chunk_size` alinhado aos tamanhos do experimento; overlap via `overlap_sentences`.
- **Semantic:** eixo principal = `breakpoint_percentile` + `max_chunk_size`.
- **Structure-aware:** eixo principal = estrutura do documento; para comparação em não-Lattes, documentar `fallback_chunk_size` / `fallback_overlap`.

**Instanciação via API/registry**

```python
from models.enums import ChunkingStrategy
from core.chunking.registry import get_chunker

get_chunker(ChunkingStrategy.fixed_size, chunk_size=512, chunk_overlap=50)
get_chunker(ChunkingStrategy.recursive, chunk_size=512, chunk_overlap=50)
get_chunker(ChunkingStrategy.sentence, max_chunk_size=512, overlap_sentences=1)
get_chunker(ChunkingStrategy.semantic, breakpoint_percentile=25, max_chunk_size=1024)
get_chunker(
    ChunkingStrategy.structure_aware,
    max_chunk_size=1024,
    fallback_chunk_size=512,
    fallback_overlap=50,
)
```
