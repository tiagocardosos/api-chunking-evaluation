### 4. API-SPEC.md (detalhando os endpoints mínimos que você pediu)

```markdown
# Especificação da API – Endpoints Mínimos e Funcionais

## Estrutura de Pastas (exata)
backend/api/routes/
├── documents.py      # upload + ingestão
├── collections.py    # CRUD básico de collections
├── chunking.py       # escolher estratégia e preview de chunks
├── search.py         # busca semântica + híbrida
├── rag.py            # RAG completo (retrieval + generation)
└── experiments.py    # rodar experimento simples (1 config)

## Endpoints Obrigatórios (prioridade Dia 1)

POST /documents/ingest
- Recebe arquivo (PDF ou XML) + collection_id + chunking_strategy
- Retorna: document_id + quantidade de chunks criados + preview

GET /documents/{doc_id}/chunks
- Preview dos chunks gerados (essencial para validar structure-aware)

POST /search
- query + collection_id + strategy (semantic/hybrid)
- Retorna top_k resultados com score

POST /rag/chat
- query + collection_id + chunking_strategy
- Retorna resposta + contexto recuperado + métricas

POST /experiments/run
- Recebe JSON de config (chunking, embedding, top_k, etc.)
- Executa + salva resultados no Postgres + retorna métricas RAGAS

**Todos os endpoints usam Pydantic v2 e retornam JSON padronizado.**
**Autenticação: nenhuma (local)**
