# RAG Chunking Evaluation – Projeto Acadêmico IA Generativa (Mestrado)

**Repositório oficial do artigo:** Avaliação de Estratégias de Chunking em Sistemas RAG para Documentos Institucionais Brasileiros (PDFs + XMLs Lattes)

**Autores:** Tiago + Alan (coautoria possível: George Hideyuki Kuroki Júnior – tese UNB 2023)

**Objetivo principal:**  
Comparar 5 estratégias de chunking (fixed-size, recursive, sentence, semantic e structure-aware) em documentos reais de fomento à inovação (EMBRAPII + currículos Lattes CNPq) e medir impacto em recuperação e qualidade de resposta RAG.

**Foco acadêmico:** Não é uma ferramenta — é um **experimento reproduzível** com golden set anotado, métricas RAGAS + estatística (Alan).

**Stack (tudo local via Docker):**
- FastAPI (Python 3.12)
- Qdrant (vector store)
- PostgreSQL (metadados + resultados de experimentos)
- LangChain (loaders + splitters)
- OpenAI API (embeddings + geração)
- RAGAS + custom metrics

**Como rodar (em 30 segundos):**
```bash
cp .env.example .env
# edite .env e insira sua OPENAI_API_KEY
docker compose up -d
```
