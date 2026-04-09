# RAG Chunking Evaluation

Experimento acadêmico de mestrado que compara **5 estratégias de chunking** em sistemas RAG aplicados a documentos institucionais brasileiros: editais PDF da EMBRAPII e currículos Lattes (JSON/XML) do CNPq.

> **Pergunta de pesquisa:** Como diferentes estratégias de chunking afetam a qualidade de recuperação e geração em documentos institucionais brasileiros?

---

## Estratégias avaliadas

| Estratégia | Descrição |
|---|---|
| `fixed_size` | Divisão por caracteres com overlap fixo — baseline do experimento |
| `recursive` | Hierarquia de separadores adaptada para português (LangChain) |
| `sentence` | Split por sentenças com proteção a abreviações pt-BR |
| `semantic` | Quebras detectadas por queda de similaridade semântica (OpenAI embeddings) |
| `structure_aware` | 1 chunk por produção científica — exclusivo para Lattes (JSON/XML) |

## Métricas

- **RAGAS**: Faithfulness, Answer Relevancy, Context Precision, Context Recall, Answer Correctness
- **MRR** e **Recall@5** (heurística de janela de tokens sobre `expected_answer`)
- **Wilcoxon signed-rank pareado** + correção Holm-Bonferroni para comparações múltiplas

---

## Stack

| Componente | Tecnologia |
|---|---|
| API | FastAPI + Python 3.12 |
| Vector store | Qdrant |
| Banco relacional | PostgreSQL 16 + SQLAlchemy 2.0 |
| Embeddings | `text-embedding-3-small` (OpenAI, 1536 dims) |
| Gerador | `gpt-4o-mini` (temperature=0, seed=42) |
| Avaliação | RAGAS + métricas customizadas |
| Pacotes | uv |
| Infra local | Docker Compose |

---

## Requisitos

- Docker + Docker Compose
- Chave de API da OpenAI (`OPENAI_API_KEY`)

---

## Início rápido

```bash
# 1. Clonar e configurar variáveis de ambiente
git clone <repo-url>
cd rag-chunking-evaluation-mestrado
cp .env.example .env
# edite .env e insira sua OPENAI_API_KEY

# 2. Subir os serviços
docker compose up -d

# 3. Verificar que a API está respondendo
curl http://localhost:8000/health
```

Serviços disponíveis após `docker compose up`:

| Serviço | URL |
|---|---|
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Estrutura do projeto

```
backend/
  api/routes/         # endpoints FastAPI
  core/
    chunking/         # 5 estratégias + registry
    loaders/          # pdf_loader, xml_loader, json_lattes_loader
    embeddings.py     # OpenAIEmbedder
    ingestor.py       # pipeline de ingestão
    evaluator.py      # RAGAS + MRR
    experiment_runner.py
  models/             # ORM SQLAlchemy + schemas Pydantic
data/
  lattes/             # 23 currículos Lattes em JSON (exemplos)
evaluation/
  wilcoxon.py         # testes estatísticos
  tables.py           # exportação CSV / LaTeX
  golden_set_example.json
docs/
  PAPER-NOTES.md      # decisões metodológicas para o artigo
  TESTES-MANUAIS.md   # roteiro de testes com comandos reproduzíveis
  API-SPEC.md
  CHUNKING-STRATEGIES.md
  EXPERIMENT-SPEC.md
```

---

## Fluxo do experimento

```
1. Criar coleção        POST /collections
2. Ingerir documentos   POST /documents/ingest   (PDF ou JSON Lattes)
3. Disparar experimento POST /experiments/run    (retorna HTTP 202)
4. Monitorar            GET  /experiments/{id}
5. Resultados           GET  /experiments/{id}   (status=completed)
```

### Exemplo completo — 23 Lattes em lote

```bash
# 1. Criar coleção
curl -s -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "Lattes - structure_aware"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"

# 2. Ingerir todos os arquivos
COLLECTION_ID="<id>"
for f in data/lattes/*.json; do
  curl -s -X POST http://localhost:8000/documents/ingest \
    -F "file=@$f;type=application/json" \
    -F "collection_id=$COLLECTION_ID" \
    -F "chunking_strategy=structure_aware" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d['filename'], d['total_chunks'], 'chunks')"
done

# 3. Rodar experimento
curl -s -X POST http://localhost:8000/experiments/run \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Demo Lattes\",
    \"collection_id\": \"$COLLECTION_ID\",
    \"chunking_strategy\": \"structure_aware\",
    \"top_k\": 5,
    \"golden_questions\": [
      {\"question\": \"Quais pesquisadores têm orientações concluídas de mestrado?\",
       \"question_type\": \"inferential\"}
    ]
  }" | python3 -c "import sys,json; print('experiment_id:', json.load(sys.stdin)['experiment_id'])"

# 4. Acompanhar
curl -s http://localhost:8000/experiments/<experiment_id> \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d.get('avg_faithfulness'))"
```

> Veja `docs/TESTES-MANUAIS.md` para o roteiro completo com todos os comandos e resultados esperados.

---

## Executar comandos no container

Todos os comandos de desenvolvimento rodam dentro do container via `docker exec`:

```bash
# Testes
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run pytest tests/ -v

# Linting
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff check .

# Adicionar dependência
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv add <pacote>
```

---

## Análise estatística

Após coletar resultados de múltiplos experimentos:

```bash
# Dentro do diretório evaluation/
python3 run_analysis.py          # Wilcoxon + Holm-Bonferroni
python3 tables.py                # gera CSV, Markdown e LaTeX
```

---

## Decisões metodológicas

Consulte `docs/PAPER-NOTES.md` para justificativas das escolhas técnicas relevantes para a seção de Metodologia do artigo: modelo de embedding, gerador, métricas, design do golden set e análise estatística.

---

## Autores

Tiago Cardoso · Alan Robson — Mestrado em Ciência da Computação
