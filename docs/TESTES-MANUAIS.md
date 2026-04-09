# Testes Manuais — Roteiro de Repetição

Documento vivo: registra os testes realizados manualmente durante o desenvolvimento,
com os comandos exatos para reproduzi-los.

Pré-requisito: `docker compose up -d` rodando (fastapi:8000, qdrant:6333, postgres:5432).

---

## Índice

1. [Ingestão de um único arquivo Lattes](#1-ingestão-de-um-único-arquivo-lattes)
2. [Ingestão em lote — todos os Lattes](#2-ingestão-em-lote--todos-os-lattes)
3. [Execução de experimento](#3-execução-de-experimento)
4. [Monitoramento do experimento](#4-monitoramento-do-experimento)
5. [Leitura dos resultados](#5-leitura-dos-resultados)
6. [Busca semântica direta](#6-busca-semântica-direta)
7. [Preview de chunks sem ingerir](#7-preview-de-chunks-sem-ingerir)
8. [Deleção e re-ingestão](#8-deleção-e-re-ingestão)

---

## 1. Ingestão de um único arquivo Lattes

Cria a coleção e ingere um único JSON para validar o pipeline antes do lote.

```bash
# 1a. Criar coleção
curl -s -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lattes JSON - structure_aware",
    "description": "Currículos Lattes em JSON, chunking structure_aware"
  }' | python3 -m json.tool
# → anote o "id" retornado como COLLECTION_ID

# 1b. Ingerir um arquivo
COLLECTION_ID="<id-da-colecao>"
curl -s -X POST http://localhost:8000/documents/ingest \
  -F "file=@data/lattes/2420063492215189.json;type=application/json" \
  -F "collection_id=$COLLECTION_ID" \
  -F "chunking_strategy=structure_aware" \
  -o /tmp/ingest_result.json

python3 -c "
import json
d = json.load(open('/tmp/ingest_result.json'))
print('document_id :', d['document_id'])
print('doc_type    :', d['doc_type'])
print('total_chunks:', d['total_chunks'])
print()
for c in d['preview']:
    print(f'  chunk {c[\"chunk_index\"]} ({c[\"chunk_metadata\"].get(\"section_type\",\"?\")}):')
    print(f'    {c[\"content\"][:120]}')
"
```

**Resultado esperado (arquivo `2420063492215189.json` — Giulia Naranjo Aranha):**
- `doc_type: json_lattes`
- `total_chunks: 51` (varia com `max_chunk_size`)
- Preview: chunk 0 = `DADOS-GERAIS`, chunks seguintes = artigos/trabalhos

---

## 2. Ingestão em lote — todos os Lattes

Ingere todos os 23 arquivos `data/lattes/*.json` na mesma coleção.

```bash
COLLECTION_ID="<id-da-colecao>"
LATTES_DIR="data/lattes"
TOTAL_CHUNKS=0; SUCCESS=0; FAIL=0

for f in "$LATTES_DIR"/*.json; do
  fname=$(basename "$f")
  curl -s -X POST http://localhost:8000/documents/ingest \
    -F "file=@$f;type=application/json" \
    -F "collection_id=$COLLECTION_ID" \
    -F "chunking_strategy=structure_aware" \
    -o /tmp/ingest_result.json

  read chunks detail < <(python3 - <<'PY'
import json, sys
try:
    d = json.load(open("/tmp/ingest_result.json"))
    if "total_chunks" in d:
        print(d["total_chunks"], "")
    else:
        print("", d.get("detail", "unknown error"))
except Exception as e:
    print("", str(e))
PY
)

  if [ -n "$chunks" ] && [ "$chunks" != "" ]; then
    TOTAL_CHUNKS=$((TOTAL_CHUNKS + chunks))
    SUCCESS=$((SUCCESS + 1))
    echo "OK  $fname → $chunks chunks"
  else
    FAIL=$((FAIL + 1))
    echo "ERR $fname → $detail"
  fi
done

echo ""
echo "Resultado: $SUCCESS OK, $FAIL erros | Total chunks: $TOTAL_CHUNKS"
```

**Resultado esperado (23 arquivos, `structure_aware`, `max_chunk_size=1024`):**

| Arquivo | Pesquisador | Chunks |
|---|---|---|
| 2420063492215189.json | Giulia Naranjo Aranha | 51 |
| 2420281167781382.json | Lidiane Miranda Rocha | 16 |
| 2420383010340040.json | Laíne Garcia Ferreira | 132 |
| 2421401938215444.json | Juliana R. T. Dantas Sartori | 10 |
| 2421723292782050.json | Marcus Vinicius de Paula | 177 |
| 2421927797042514.json | Guilherme H. de Melo Gurjão | 32 |
| 2422090223041647.json | Eugenio de Castro | 17 |
| 2422490836174594.json | Gibran da Cunha Vasconcelos | 108 |
| 2422663966558910.json | Sabrina C. de Freitas Adriano | 14 |
| 2423047534307015.json | Tayara Dias Silveira | 25 |
| 2423253938089123.json | Magno Miranda Dantas | 11 |
| 2423262476812988.json | Alan Robson Da Silva | 41 |
| 2424584893833728.json | Thiago Scodeler | 28 |
| 2424813779338621.json | Marcus Hilson da Silva Caxias | 50 |
| 2425616691966823.json | Luísa Mayumi Hasegawa de Freitas | 29 |
| 2427238180441437.json | Tamires Aline de Oliveira | 13 |
| 2427644009008611.json | Elcimar Pessoa Rocha | 228 |
| 2427994326399498.json | Vitor Hugo Lemes Nascimento | 11 |
| 2428697668206354.json | Estevan Linck Lara | 26 |
| 2429488819603264.json | Antonio Pedro de Abreu Neto | 4 |
| 2429559672980233.json | Cedric Salotto Cordeiro | 5 |
| 2429691083234366.json | Thiago Teixeira da Silva | 17 |
| 2429856261320761.json | Jean Jefferson Moraes da Silva | 92 |
| **Total** | | **1.137** |

---

## 3. Execução de experimento

Inicia o experimento em background (HTTP 202). Substitua `COLLECTION_ID` e ajuste
as perguntas conforme o corpus ingerido.

```bash
COLLECTION_ID="<id-da-colecao>"

curl -s -X POST http://localhost:8000/experiments/run \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Demo - Lattes structure_aware\",
    \"collection_id\": \"$COLLECTION_ID\",
    \"chunking_strategy\": \"structure_aware\",
    \"top_k\": 5,
    \"golden_questions\": [
      {
        \"question\": \"Quais artigos foram publicados por Jean Jefferson?\",
        \"question_type\": \"factual\"
      },
      {
        \"question\": \"Em qual instituição Giulia Naranjo Aranha fez mestrado?\",
        \"expected_answer\": \"Universidade Federal do Rio de Janeiro\",
        \"question_type\": \"factual\"
      },
      {
        \"question\": \"Quais são as áreas de atuação de Marcus Vinicius de Paula?\",
        \"question_type\": \"factual\"
      },
      {
        \"question\": \"Quais pesquisadores têm orientações concluídas de mestrado?\",
        \"question_type\": \"inferential\"
      },
      {
        \"question\": \"Qual o título da dissertação de mestrado de Giulia Naranjo Aranha?\",
        \"expected_answer\": \"Caracterização estrutural e funcional do gene orfE264\",
        \"question_type\": \"factual\"
      }
    ]
  }" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('experiment_id:', d['experiment_id'])
print('status       :', d['status'])
print('total_questions:', d['total_questions'])
"
# → anote o experiment_id
```

---

## 4. Monitoramento do experimento

Faz polling até `completed` ou `failed` (intervalo de 10s, máximo ~4min).

```bash
EXPERIMENT_ID="<experiment-id>"

for i in $(seq 1 30); do
  curl -s "http://localhost:8000/experiments/$EXPERIMENT_ID" \
    -o /tmp/exp_status.json

  status=$(python3 -c "import json; d=json.load(open('/tmp/exp_status.json')); print(d['status'])")
  total=$(python3 -c "import json; d=json.load(open('/tmp/exp_status.json')); print(d['total_questions'])")
  echo "[$i] status=$status questions=$total"

  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    break
  fi
  sleep 10
done
```

**Tempo esperado para 5 perguntas:** ~60–90 s (embed + RAG + RAGAS por pergunta).

---

## 5. Leitura dos resultados

Exibe métricas agregadas e resultado por pergunta.

```bash
python3 - <<'PY'
import json

d = json.load(open("/tmp/exp_status.json"))

print("=" * 60)
print(f"Experimento : {d['name']}")
print(f"Status      : {d['status']}  |  Perguntas: {d['total_questions']}")
print("=" * 60)

metrics = [
    ("Faithfulness",       d.get("avg_faithfulness")),
    ("Answer Relevancy",   d.get("avg_answer_relevancy")),
    ("Context Precision",  d.get("avg_context_precision")),
    ("Context Recall",     d.get("avg_context_recall")),
    ("Answer Correctness", d.get("avg_answer_correctness")),
]
print("\nMétricas agregadas:")
for name, val in metrics:
    if val is not None:
        bar = "█" * int(val * 20)
        print(f"  {name:<22} {bar:<20}  {val:.2f}")
    else:
        print(f"  {name:<22} {'—':>22}  (sem ground truth)")

print("\n" + "─" * 60)
for i, r in enumerate(d.get("results", []), 1):
    print(f"\n[Q{i}] {r['question']}")
    print(f"  ↳ {r['generated_answer'][:200]}{'...' if len(r['generated_answer']) > 200 else ''}")
    parts = [f"{k}={v:.2f}" for k, v in {
        "faith" : r.get("faithfulness"),
        "rel"   : r.get("answer_relevancy"),
        "prec"  : r.get("context_precision"),
        "recall": r.get("context_recall"),
        "corr"  : r.get("answer_correctness"),
        "mrr"   : r.get("mrr"),
    }.items() if v is not None]
    print(f"  Métricas: {', '.join(parts) if parts else '(aguardando)'}")
PY
```

**Resultado obtido em 09/04/2026 (23 Lattes, structure_aware, 5 perguntas):**

| Métrica | Valor | Observação |
|---|---|---|
| Faithfulness | 0.70 | respostas ancoradas no contexto |
| Answer Relevancy | 0.18 | baixo — 4/5 retornaram "não encontrado" |
| Context Precision | 0.20 | retrieval trouxe chunks de outros pesquisadores |
| Context Recall | 0.00 | ground truth só em 2 perguntas, MRR=0 |
| Answer Correctness | 0.12 | direto reflexo do recall |

**Análise:** retrieval semântico puro com `top_k=5` em 1.137 chunks de 23 pesquisadores
não consegue isolar o pesquisador correto quando o nome é mencionado na pergunta.
Perguntas por conceito (Q4: "orientações concluídas") funcionam muito melhor.
Isso é esperado e documenta uma limitação do retrieval denso sem filtro por `document_id`.

---

## 6. Busca semântica direta

Testa o retrieval isolado, sem geração.

```bash
COLLECTION_ID="<id-da-colecao>"

curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"orientações concluídas de mestrado\",
    \"collection_id\": \"$COLLECTION_ID\",
    \"top_k\": 5
  }" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d['results']:
    print(f'score={r[\"score\"]:.3f}  section={r[\"chunk_metadata\"].get(\"section_type\",\"?\")}')
    print(f'  {r[\"content\"][:100]}')
    print()
"
```

---

## 7. Preview de chunks sem ingerir

Útil para validar visualmente como uma estratégia divide um arquivo antes de ingerir.

```bash
curl -s -X POST http://localhost:8000/chunking/preview \
  -F "file=@data/lattes/2429856261320761.json;type=application/json" \
  -F "chunking_strategy=structure_aware" \
  -o /tmp/preview.json

python3 -c "
import json
d = json.load(open('/tmp/preview.json'))
print(f'total_chunks: {d[\"total_chunks\"]}')
for c in d['chunks'][:5]:
    print(f'\n  [{c[\"chunk_index\"]}] {c[\"chunk_metadata\"].get(\"section_type\",\"?\")} ({len(c[\"content\"])} chars)')
    print(f'  {c[\"content\"][:150]}')
"
```

---

## 8. Deleção e re-ingestão

Para refazer os testes do zero.

```bash
COLLECTION_ID="<id-da-colecao>"

# Deletar a coleção (remove do Postgres + Qdrant via cascade no experimento)
curl -s -X DELETE "http://localhost:8000/collections/$COLLECTION_ID"

# Recriar e re-ingerir conforme seções 1–2
```

> **Nota:** a deleção da coleção no Qdrant pode ser feita diretamente pelo dashboard
> em http://localhost:6333/dashboard se preferir manter o registro no Postgres.

---

## Notas sobre os testes

### Problema encontrado: contagem baixa de chunks (09/04/2026)

Ao ingerir `2421401938215444.json` (Juliana) com `structure_aware`, o DADOS-GERAIS
aparecia com seções vazias (`[Formacao Academica Titulacao]` sem conteúdo).

**Causa:** `_serialize_json_item` não era recursivo — sub-dicts sem `@` direto
(ex: `FORMACAO-ACADEMICA-TITULACAO.GRADUACAO`) não eram percorridos.

**Correção:** substituído por `_walk_json` recursivo em
`backend/core/chunking/structure_aware.py`.

### Problema encontrado: orientações não coletadas (09/04/2026)

`2429856261320761.json` (Jean Jefferson) tinha 4 orientações em
`OUTRA-PRODUCAO.ORIENTACOES-CONCLUIDAS.OUTRAS-ORIENTACOES-CONCLUIDAS`
que não eram capturadas — o extrator só procurava em `DADOS-COMPLEMENTARES`.

**Correção:** adicionado `_collect_json_items_flat` para `OUTRA-PRODUCAO`
em `_extract_items_json`.

### Observação sobre retrieval (09/04/2026)

Perguntas com nome próprio específico têm retrieval ruim em coleções com
muitos pesquisadores porque o embedding semântico não discrimina nomes.
Para o golden set definitivo, preferir perguntas por conceito/área ou
usar `filter_document_id` na busca.
