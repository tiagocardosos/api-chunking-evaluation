# Notas para o Artigo — Decisões de Implementação e Metodologia

Documento vivo: registra decisões técnicas tomadas durante a implementação
que impactam diretamente a seção de Metodologia do artigo.
Atualizar sempre que uma decisão relevante for alterada.

---

## 1. Variáveis Fixadas (não variam entre experimentos)

| Variável | Valor | Justificativa |
|---|---|---|
| Modelo de embedding | `text-embedding-3-small` (1536 dims) | Custo-benefício; estado da arte entre os modelos OpenAI de menor custo |
| Modelo gerador | `gpt-4o-mini` | Desempenho suficiente para português; custo controlável em 180 × N experimentos. Ollama/modelos locais descartados para manter o gerador como variável fixada e não introduzir variação de infra |
| `temperature` do gerador | `0` | Respostas determinísticas para a mesma query + contexto |
| `seed` do gerador | `42` | Camada adicional de reproducibilidade (OpenAI suporta desde 2024) |
| `top_k` | `5` | Padrão da literatura RAG; equilibra recall e ruído de contexto |
| Retrieval base | Semântico (cosine, vetor denso) | Hybrid (BM25 + denso) é variável secundária implementada mas não avaliada neste artigo |
| RAGAS LLM | `gpt-4o-mini` (idem ao gerador) | Mantém consistência; evita viés de avaliação por modelo diferente do gerador |

> **Para o artigo:** citar que embedding e gerador são variáveis de controle, não de interesse.
> A variável independente é exclusivamente a estratégia de chunking.

---

## 2. Estratégias de Chunking — Decisões de Implementação

### 2.1 FixedSizeChunker
- Divisão por **caracteres** (não por tokens).
- Justificativa: tokens dependem do tokenizador do modelo; caracteres são independentes de modelo e reproduzíveis sem dependência externa.
- Configurações do experimento: `chunk_size ∈ {256, 512, 1024}`, `overlap ∈ {0, 50, 128}`.
- Serve como **baseline** de referência para comparação estatística.

### 2.2 RecursiveCharacterChunker
- Implementado via `langchain_text_splitters.RecursiveCharacterTextSplitter`.
- Hierarquia de separadores customizada para português: `["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]`.
- Separadores padrão do LangChain são orientados ao inglês (não incluem `"; "` e priorizam `.` diferente).

### 2.3 SentenceChunker
- Split de sentenças com proteção de **abreviações em português** (Dr., Prof., Art., Fig., meses, etc.).
- Mecanismo: substitui temporariamente o ponto das abreviações por marcador `\x00` antes do regex de fronteira de sentença.
- Overlap em **nível de sentença** (não de caractere) — mais natural semanticamente.
- Parâmetro: `overlap_sentences` (default: 1 sentença).

### 2.4 SemanticChunker
- Usa **OpenAI embeddings** para detectar os pontos de quebra semântica entre sentenças (mesmo modelo do retrieval).
- Alternativa considerada: `sentence-transformers` local → **descartada** para manter o embedding como variável única e controlada.
- Custo adicional: o SemanticChunker faz chamadas à API durante a ingestão (não apenas durante o retrieval).
- Threshold de quebra: percentil das quedas de similaridade (`breakpoint_percentile=25` → poucos cortes, chunks maiores).
- Proteção contra chunks gigantes: segmentos > `max_chunk_size` são subdivididos por caractere (fallback).

### 2.5 StructureAwareChunker
- **Diferencial acadêmico do experimento**: única estratégia que explora a estrutura do documento.
- Granularidade: **1 chunk por unidade de produção científica** (artigo, livro, capítulo, patente, orientação).
- Seções de dados pessoais e formação → 1 chunk por seção.
- Atributos XML são serializados como texto legível: `"Nome Do Periodico: Journal Name"`.
- **Fallback automático** para `RecursiveCharacterChunker` quando o input não é XML Lattes.
- Hipótese a validar: vence as demais estratégias em perguntas sobre XMLs Lattes.

---

## 3. Métricas de Avaliação

### 3.1 RAGAS (via API OpenAI)
Todas as métricas RAGAS usam LLM internamente — por isso o avaliador recebe o mesmo `gpt-4o-mini` do gerador.

| Métrica | Requer `ground_truth`? | O que mede |
|---|---|---|
| Faithfulness | Não | Resposta está ancorada no contexto? |
| Answer Relevancy | Não | Resposta é relevante para a pergunta? |
| Context Precision | Não | Chunks recuperados são precisos (ranking)? |
| Context Recall | **Sim** | Contexto cobre a ground truth? |
| Answer Correctness | **Sim** | Resposta está correta vs. gabarito? |

> **Para o artigo:** perguntas sem `expected_answer` contribuem apenas para as 3 primeiras métricas.
> Anotar isso na seção de Metodologia para justificar o golden set parcialmente anotado.

### 3.2 MRR (Mean Reciprocal Rank) — Métrica Customizada
- **Problema:** não temos anotações chunk-level (apenas pares pergunta-resposta).
- **Solução adotada (heurística):** um chunk é considerado "relevante" se contém pelo menos uma janela de 5 tokens consecutivos da `expected_answer`.
- MRR_i = 1 / (posição do primeiro chunk relevante), ou 0 se nenhum for relevante.
- **Limitação a mencionar no artigo:** MRR é proxy; não substitui anotações manuais de relevância.

### 3.3 Recall@5
- Calculado junto com MRR: 1.0 se qualquer top-5 chunk contém a resposta, 0.0 caso contrário.
- Mesma heurística de janela de 5 tokens.

---

## 4. Análise Estatística

### 4.1 Teste Wilcoxon Signed-Rank (pareado)
- **Por que Wilcoxon e não t-test:** distribuições de métricas RAG não são normais (scores concentrados em 0 e 1).
- **Por que pareado:** as 180 perguntas são **idênticas** para todos os experimentos → aproveitamos a correlação intra-pergunta (maior poder estatístico que Mann-Whitney).
- Alinhamento de pares: por texto exato da pergunta (as mesmas `golden_questions` são enviadas a todos os experimentos).

### 4.2 Correção para Múltiplas Comparações — Holm-Bonferroni
- 5 estratégias → C(5,2) = **10 pares** por métrica × 6 métricas = 60 comparações.
- Holm-Bonferroni (vs. Bonferroni simples): **mesmo controle de FWER, menos conservador** → mais poder para detectar diferenças reais.
- Implementação: ordena p-values crescente; limiar_k = α / (m − k + 1).

### 4.3 Tamanho de Efeito — Rank-Biserial Correlation (r)
- r = 1 − 2W / (n×(n+1)/2), onde W é a estatística de Wilcoxon.
- Interpretação (Cohen, 1988): |r| < 0.1 trivial, 0.1–0.3 pequeno, 0.3–0.5 médio, > 0.5 grande.
- Reportar sempre junto com o p-value para evitar significância estatística sem relevância prática.

### 4.4 Análises Separadas (PDF vs. XML Lattes)
- Motivação: chunking semântico é esperado superior em PDFs; structure-aware em XMLs.
- Implementação: `results_loader.py` suporta filtros `doc_type_filter` e `question_type_filter`.
- Requer que o golden set anote `doc_type` e `question_type` para cada pergunta.

---

## 5. Design de Dados

### 5.1 Uma estratégia por coleção
- Cada coleção Qdrant contém documentos ingeridos com **uma única estratégia**.
- Justificativa: isola completamente o impacto da estratégia; evita contaminação cruzada no índice vetorial.
- Implicação para o experimento: para comparar 5 estratégias com 100 documentos, criar 5 coleções separadas.

### 5.2 Chunks duplicados (PostgreSQL + Qdrant)
- PostgreSQL armazena o conteúdo textual dos chunks para auditoria e validação visual (endpoint `GET /documents/{id}/chunks`).
- Qdrant armazena o vetor + payload (conteúdo + metadados) para retrieval.
- Justificativa: permite inspecionar e depurar o StructureAwareChunker sem consultar o Qdrant.

### 5.3 Experimentos em Background
- `POST /experiments/run` retorna HTTP 202 imediatamente; a execução ocorre em `BackgroundTask`.
- Motivação: 180 perguntas × (1 embed + 1 search + 1 generate + RAGAS eval) ≈ 700–900 chamadas API → pode levar 15–30 min.
- Estado do experimento monitorável via `GET /experiments/{id}`.

---

## 6. Limitações Conhecidas (para a seção de Limitações do artigo)

1. **Hybrid search incompleto:** a rota `/search` com `retrieval_strategy=hybrid` atualmente faz fallback para semântico puro (BM25 sparse vectors não implementados). Reportar como trabalho futuro ou implementar antes da submissão.

2. **MRR por heurística:** sem anotações chunk-level, o MRR é calculado por correspondência de texto com a ground_truth. Pode subestimar a relevância de chunks que respondem a pergunta de forma parafraseada.

3. **Custo do SemanticChunker:** usa chamadas OpenAI na fase de ingestão (não só no retrieval). Em 100 documentos com ~200 sentenças cada = ~20.000 embeddings extras. Deve ser mencionado como trade-off.

4. **Encoding XML Lattes:** a detecção de encoding é heurística (lê o cabeçalho XML). XMLs corrompidos ou com encoding incorretamente declarado podem falhar silenciosamente — fallback para Latin-1.

5. **Golden set anotado parcialmente:** perguntas sem `expected_answer` contribuem apenas para 3 das 5 métricas RAGAS. Impacta diretamente Context Recall e Answer Correctness.

---

## 7. Reprodutibilidade — Checklist

- [ ] Docker Compose com versões fixadas (`postgres:16-alpine`, `qdrant/qdrant:latest`)
- [x] `temperature=0, seed=42` no gerador (GPT-4o-mini)
- [x] `temperature=0` no avaliador RAGAS
- [ ] `OPENAI_API_KEY` documentada no `.env.example`
- [ ] Seed fixo no `numpy` e `random` para splits determinísticos (verificar se necessário)
- [ ] Versões dos pacotes fixadas em `uv.lock` antes da submissão
- [ ] Golden set versionado no repositório (ou link DOI se muito grande)

---

## 8. Pendências (Alan)

- [ ] Criar `evaluation/golden_set.json` com 180 perguntas reais
  - 90 factual/procedimental + 90 inferencial
  - Cobrir ambos os tipos de documento (`pdf` e `xml_lattes`)
  - Anotar `expected_answer` para o maior número possível (impacta 2 métricas RAGAS)
  - Usar `evaluation/golden_set_example.json` como referência de formato
- [ ] Revisar abreviações pt-BR no `SentenceChunker` (`sentence.py:_PT_ABBREVIATIONS`)
- [ ] Validar amostras do `StructureAwareChunker` em XMLs Lattes reais

---

## 9. Referências de Implementação

| Componente | Arquivo | Linha-chave |
|---|---|---|
| Classe abstrata chunker | `backend/core/chunking/base.py` | `BaseChunker.split()` |
| Registry de estratégias | `backend/core/chunking/registry.py` | `get_chunker()` |
| Abreviações pt-BR | `backend/core/chunking/sentence.py` | `_PT_ABBREVIATIONS` |
| Threshold semântico | `backend/core/chunking/semantic.py` | `breakpoint_percentile` |
| Parser XML Lattes | `backend/core/chunking/structure_aware.py` | `_extract_items()` |
| RAGAS wrapper | `backend/core/evaluator.py` | `evaluate_with_ragas()` |
| MRR heurístico | `backend/core/evaluator.py` | `compute_mrr()` |
| Wilcoxon + Holm | `evaluation/wilcoxon.py` | `run_all_comparisons()` |
| Tabelas LaTeX | `evaluation/tables.py` | `save_all()` |
