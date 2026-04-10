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
- 180 golden questions: **90 no bloco factual** (fatos explícitos + perguntas procedimentais) **+ 90 inferenciais**
- Cada item do golden set inclui `doc_type` (`pdf` | `xml_lattes`) para análise separada PDF vs XML
- Formato e validação: `evaluation/golden_set_loader.py` e `evaluation/golden_set_example.json`

### 4.1 Campo `question_type` (implementação vs. desenho)

No JSON do golden set e na API existem **apenas dois valores** válidos: `factual` e `inferential`. O texto “factual/procedimental” do plano refere-se ao **conteúdo** das 90 primeiras perguntas, não a um terceiro enum.

| Valor no JSON | O que cobre | Exemplos |
|---------------|-------------|----------|
| `factual` | Fatos explícitos no documento (datas, números, nomes, definições) **e** perguntas **procedimentais** (critérios, requisitos, passos, elegibilidade) cuja resposta está ancorada no texto | “Qual o prazo máximo…?”, “Quais os critérios de elegibilidade…?” |
| `inferential` | Síntese, interpretação, comparação ou raciocínio sobre o conteúdo; resposta raramente é uma única citação literal | Impacto de políticas no risco; evolução da produção ao longo da carreira |

**`expected_answer`:** preferível preencher para `factual` (métricas RAGAS que usam ground truth, ex. Context Recall e Answer Correctness). Para `inferential`, o gabarito pode ser `null` quando a resposta de referência for difícil de fixar; nesse caso as métricas sem `ground_truth` ainda se aplicam (ver `docs/PAPER-NOTES.md` §3.1).

**Análise estatística:** `evaluation/results_loader.py` aceita filtro `question_type` (`factual` | `inferential`) quando essas colunas estiverem disponíveis nos resultados alinhados ao golden set.

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
