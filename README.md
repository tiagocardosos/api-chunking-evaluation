# RAG Chunking Evaluation — Backend

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-vector_store-FF4154)](https://qdrant.tech/)
[![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)](https://platform.openai.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9)](https://docs.astral.sh/uv/)
[![RAGAS](https://img.shields.io/badge/RAGAS-evaluation-F97316)](https://docs.ragas.io/)
[![Status](https://img.shields.io/badge/Status-Em_desenvolvimento-green)]()

Backend de experimentação para avaliação comparativa de **5 estratégias de chunking** em sistemas RAG (Retrieval-Augmented Generation) aplicados a documentos institucionais brasileiros.

Desenvolvido como parte de dissertação do **Mestrado em Administração Pública: Ciência de Dados e Inteligência Artificial no Setor Público**.

O corpus de teste inclui documentos normativos da EMBRAPII (PDF) e currículos Lattes (JSON/XML) da Plataforma Lattes/CNPq. A qualidade de cada estratégia é medida pelas métricas do framework RAGAS e por testes estatísticos pareados (Wilcoxon + Holm-Bonferroni).

> **Pergunta de pesquisa:** Como diferentes estratégias de chunking afetam a qualidade de recuperação e geração em documentos institucionais brasileiros?

---

## Frontend — RAG Orbit

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TanStack Start](https://img.shields.io/badge/TanStack_Start-v1-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/start)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Bun](https://img.shields.io/badge/Bun-runtime-F9F1E1?logo=bun&logoColor=black)](https://bun.sh/)

O **[RAG Orbit](https://github.com/tiagocardosos/rag-orbit)** é a interface web do projeto — uma plataforma interativa para configurar experimentos, visualizar resultados e explorar o corpus de forma intuitiva. Consome exclusivamente esta API.

**Funcionalidades principais:**

- **Dashboard (Solar System)** — visualização orbital das estratégias com métricas agregadas
- **Chunking Lab** — comparação visual de distribuição de tamanho dos chunks
- **Busca Semântica** — interface para testar buscas vetoriais no corpus
- **RAG Chat** — chat com o sistema RAG para testar respostas em tempo real
- **Experimentos** — configuração e disparo de avaliações RAGAS
- **Resultados** — heatmaps, box-plots, radar charts e testes estatísticos (Wilcoxon)
- **Golden Set** — gerenciamento das 231 perguntas de avaliação (factuais e inferenciais)

> O frontend não funciona sem este backend em execução em `http://localhost:8000`.

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
git clone https://github.com/tiagocardosos/api-chunking-evaluation
cd api-chunking-evaluation
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
  golden_questions/   # PDFs e golden sets de avaliação
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
# Wilcoxon + Holm-Bonferroni + critérios de sucesso
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
  uv run python evaluation/run_analysis.py

# Filtra só PDFs ou só Lattes
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
  uv run python evaluation/run_analysis.py --doc-type pdf

# Gera tabelas CSV / Markdown / LaTeX em evaluation/outputs/
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
  uv run python evaluation/tables.py
```

> Os scripts lêem os resultados direto do PostgreSQL interno do container.
> O diretório `evaluation/` é montado em `/app/evaluation` via volume.

---

## Decisões metodológicas

Consulte `docs/PAPER-NOTES.md` para justificativas das escolhas técnicas relevantes para a seção de Metodologia do artigo: modelo de embedding, gerador, métricas, design do golden set e análise estatística.

---

## Autores

**Tiago Cardoso Soares** · **Alan Tulio Lino Gonçalves**

Mestrado em Administração Pública: Ciência de Dados e Inteligência Artificial no Setor Público
