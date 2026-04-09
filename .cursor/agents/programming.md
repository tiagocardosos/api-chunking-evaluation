---
name: programming
description: Regras e padroes de programacao para todo o projeto. Aplica-se automaticamente a todas as tarefas relacionadas a codigo.
alwaysApply: true
---

# Regras de Programacao

**Padroes obrigatorios para todo codigo deste projeto.**

---

## Stack do Projeto

| Componente | Tecnologia |
|------------|-----------|
| Linguagem | Python 3.12+ |
| Framework | FastAPI |
| Validacao | Pydantic v2 |
| Vector DB | Qdrant |
| Banco relacional | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| LLMs / Embeddings | OpenAI (`gpt-4o-mini` + `text-embedding-3-small`) |
| Pacotes | uv |
| Linting/Format | Ruff |
| Testes | pytest + pytest-asyncio |
| Infra | Docker Compose (local) |

## Documentacao de Referencia

Antes de implementar, consultar:
- `docs/API-SPEC.md` - Endpoints e estrutura de rotas
- `docs/INFRA-DOCKER.md` - Servicos Docker e portas
- `docs/CHUNKING-STRATEGIES.md` - 5 estrategias de chunking
- `docs/EXPERIMENT-SPEC.md` - Plano tecnico do experimento

---

## Regras Criticas

### 1. TUDO roda via Docker Compose

**NUNCA executar comandos Python, uv, pytest ou scripts diretamente no host.**
**SEMPRE executar dentro do container via `docker compose exec` ou `docker compose run`.**

O nome do servico da API no docker-compose e `fastapi`.

```bash
# Executar comandos no container
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run pytest -v --tb=short
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff check .
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run python scripts/batch_ingest.py

# Adicionar dependencias (requer rebuild apos)
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv add <pacote>
docker compose down && docker compose build fastapi && docker compose up -d

# Logs
docker compose logs -f fastapi
```

**Motivo:** O ambiente local (host) nao tem venv funcional nem acesso ao PostgreSQL/Qdrant. Tudo esta dentro do Docker.

### 2. Gerenciamento de Dependencias (uv)

**SEMPRE usar uv. NUNCA usar pip diretamente.**

```bash
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv add <pacote>           # adicionar
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv add --dev <pacote>      # dev
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv remove <pacote>         # remover
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv sync                    # sincronizar
```

Apos alterar dependencias, rebuildar a imagem:
```bash
docker compose down && docker compose build fastapi && docker compose up -d
```

### 2. Modificacao de Codigo

So alterar o que foi explicitamente solicitado. Nao refatorar, renomear ou reorganizar codigo adjacente sem ser pedido.

### 3. Migrations

- NUNCA alterar migrations ja aplicadas (Alembic)
- NUNCA editar arquivos de migration existentes
- SEMPRE criar nova migration para alteracoes

### 4. Multiplas Classes

Quando um modulo tem mais de uma classe, cada classe em arquivo separado:

```python
# ERRADO: multiplas classes no mesmo arquivo
backend/models/models.py:
  - Document, Collection, Experiment

# CORRETO: uma classe por arquivo
backend/models/
  __init__.py        # from .document import Document; ...
  document.py        # class Document
  collection.py      # class Collection
  experiment.py      # class Experiment
```

### 5. Linting e Formatacao (Ruff)

```bash
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff check .
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff check --fix .
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff format .
```

Rodar **antes de todo commit**.

### 6. Testes

- Cobertura minima: 80% por arquivo (meta: 90%+)
- Framework: pytest + pytest-asyncio + pytest-cov
- Executar:

```bash
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run pytest -v --tb=short
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run pytest --cov=backend --cov-report=term-missing
```

### 7. Padroes de Codigo

- Type hints em todas as assinaturas de funcao
- Pydantic v2 para validacao (nunca dicts crus)
- `async def` somente para I/O nao-bloqueante
- Nomes descritivos (ingles para codigo, portugues para docs)
- Sem comentarios obvios - codigo auto-documentado
- Early return para condicoes de erro
- Guard clauses para pre-condicoes
- Preferir funcoes puras e composicao sobre classes desnecessarias
- Pattern RORO: receber Pydantic model, retornar Pydantic model

### 8. Padroes FastAPI

- Usar lifespan context manager (nao `@app.on_event`)
- Usar dependency injection do FastAPI para estado e recursos compartilhados
- HTTPException para erros esperados com status codes especificos
- Middleware para logging e tratamento de erros inesperados
- Operacoes async para todas as chamadas a banco e APIs externas

### 9. Variaveis de Ambiente

- NUNCA credenciais hardcoded
- Usar `.env` com pydantic-settings
- `.env` sempre no `.gitignore`
- NUNCA sobrescrever `.env` sem confirmar com o usuario

---

## Estrutura de Pastas

```
backend/
  api/routes/          # endpoints FastAPI
  core/chunking/       # estrategias de chunking (registry)
  models/              # SQLAlchemy models
  schemas/             # Pydantic v2 schemas
  config.py            # configuracao (pydantic-settings)
  database.py          # conexao PostgreSQL async
  main.py              # app FastAPI
evaluation/            # RAGAS runner e metricas
docs/                  # especificacoes tecnicas
tests/                 # pytest
docker-compose.yml     # servicos locais
pyproject.toml         # dependencias (uv)
```
