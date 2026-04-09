# CLAUDE.md — Instruções para Claude Code

## Execução de Comandos

**NUNCA executar Python, uv, pytest ou scripts diretamente no host.**
**SEMPRE usar `docker exec` com o serviço `fastapi`:**

```bash
# Testes
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run pytest tests/ -v --tb=short

# Linting / formatação
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff check .
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv run ruff format .

# Adicionar dependência (rebuildar após)
docker exec rag-chunking-evaluation-mestrado-fastapi-1 uv add <pacote>
```

Motivo: o host não tem venv funcional nem acesso ao PostgreSQL/Qdrant — tudo roda dentro do Docker.

## Pacotes

Usar **uv** exclusivamente. Nunca `pip install`.

## Stack

- Python 3.12 / FastAPI / Pydantic v2
- PostgreSQL 16 + SQLAlchemy 2.0 / Qdrant
- OpenAI (`text-embedding-3-small` + `gpt-4o-mini`) — sem Ollama
- Documentos: PDFs (editais EMBRAPII) + Currículos Lattes em JSON (`data/lattes/*.json`)
