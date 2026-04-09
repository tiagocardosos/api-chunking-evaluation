# Infraestrutura Docker – Rodando Local (100% reproduzível)

## Serviços
- **fastapi**: porta 8000 (backend principal)
- **qdrant**: porta 6333 (vector DB)
- **postgres**: porta 5432 (metadados + experiment results)

## docker-compose.yml
```yaml
services:
  fastapi:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [qdrant, postgres]
    volumes: ["./backend:/app"]
    environment:
      - POSTGRES_URL=postgresql://rag:rag123@postgres:5432/rag_eval
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - .env
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: rag
      POSTGRES_PASSWORD: rag123
      POSTGRES_DB: rag_eval
    volumes: [pgdata:/var/lib/postgresql/data]

volumes:
  qdrant_data:
  pgdata:
```

## Variáveis de ambiente (.env)
```env
OPENAI_API_KEY=sk-...
POSTGRES_URL=postgresql://rag:rag123@localhost:5432/rag_eval
QDRANT_URL=http://localhost:6333
EMBEDDING_MODEL=text-embedding-3-small
GENERATOR_MODEL=gpt-4o-mini
TOP_K=5
```

## Como subir
```bash
cp .env.example .env
# edite .env e insira sua OPENAI_API_KEY
docker compose up -d
```

## Comandos úteis
```bash
# Logs do backend
docker compose logs -f fastapi

# Rodar testes
docker exec -it <container_fastapi> pytest tests/ -v

# Acessar PostgreSQL
docker exec -it <container_postgres> psql -U rag -d rag_eval

# Swagger UI
open http://localhost:8000/docs
```
