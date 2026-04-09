### 2. EXPERIMENT-SPEC.md (o Plano Técnico do Experimento – o mais importante)

```markdown
# Plano Técnico do Experimento – Chunking em RAG Institucional

## 1. Pergunta de Pesquisa
Como diferentes estratégias de chunking afetam qualidade de recuperação e geração em documentos institucionais brasileiros (PDFs editais EMBRAPII + XMLs Lattes semi-estruturados)?

## 2. Variáveis Fixas
- Embedding: text-embedding-3-small (OpenAI, 1536 dims)
- Retrieval: semantic (dense cosine) + hybrid (Qdrant sparse vectors — trabalho futuro)
- Generator: GPT-4o-mini (temperature=0, seed=42)
- top_k: 5
- Avaliação: RAGAS (Faithfulness, Answer Relevancy, Context Precision/Recall, Answer Correctness) + MRR/Recall@5

## 3. Variáveis de Chunking (foco principal – 5 estratégias)
1. Fixed-size (tamanhos 256/512/1024 + overlap 0/50/128)
2. Recursive character splitting (LangChain default)
3. Sentence-based
4. Semantic chunking
5. Structure-aware (diferencial: só para XML Lattes – respeita <secao>, <artigos>, headings)

## 4. Dataset
- 100 documentos (60 PDFs + 40 XMLs Lattes)
- 180 golden questions (90 factual/procedimental + 90 inferencial)
- Análise separada: PDF vs XML

## 5. Baselines obrigatórios
- Keyword-only (BM25)
- Sem RAG (LLM puro)

## 6. Estrutura de Pastas (seguir exatamente)
backend/api/routes/ → arquivos listados abaixo
backend/core/chunking/ → registry + estratégias
evaluation/ → RAGAS runner + análise estatística

## 7. Critérios de Sucesso
- Diferença estatística significativa (Wilcoxon signed-rank + Holm-Bonferroni)
- Structure-aware vence em XMLs Lattes
- Resultados reproduzíveis com seed fixo

**Próximos passos (cronograma real):**
- Dia 1: terminar ingestão + endpoints básicos ✓
- Dia 2-3: chunking registry + tests ✓
- Semana 5-6: golden set (Alan lidera)
```
