# Como ler os arquivos em `evaluation/outputs/`

Este diretório é preenchido por `evaluation/run_analysis.py`, que carrega resultados do PostgreSQL, calcula estatísticas descritivas e compara estratégias de chunking com o teste de **Wilcoxon signed-rank** em dados **pareados** (a mesma pergunta avaliada em cada estratégia).

Para cada tabela lógica, o script grava **três formatos com o mesmo conteúdo**:

| Extensão | Uso típico |
|----------|------------|
| `.md`    | Leitura humana no editor ou no GitHub |
| `.csv`   | Planilhas, pandas, gráficos |
| `.tex`   | Inclusão em artigo LaTeX |

Além disso existe um CSV extra com o detalhe de todas as comparações.

---

## 1. `summary.{md,csv,tex}` — Tabela 1 (descritiva)

**Título no arquivo:** "Tabela 1 — Mediana (IQR) por Estratégia".

- **Linhas:** uma por estratégia de chunking (Fixed-Size, Recursive, Semantic, Sentence, Structure-Aware quando houver dados).
- **Colunas:** métricas de avaliação do pipeline RAG.
- **Formato de cada célula:** `mediana (IQR)`, onde:
  - **Mediana** resume a distribuição dos scores por pergunta (robusta a outliers).
  - **IQR** é o intervalo interquartil (Q3 − Q1): dispersão da metade central dos valores; não é um "erro" nem desvio-padrão.

**Métricas (colunas):**

| Coluna (no resumo) | Significado em termos práticos |
|--------------------|--------------------------------|
| Faithfulness | Quão alinhada a resposta está com o contexto recuperado (consistência com as passagens). |
| Answer Relevancy | Quão perto a resposta está do que a pergunta pede. |
| Context Precision | Quão "limpo" é o contexto: quanto do recuperado é realmente útil. |
| Context Recall | Quão completo é o contexto em relação ao que seria necessário para responder. |
| Answer Correctness | Proximidade da resposta gerada em relação à resposta de referência (golden). |
| MRR (Mean Reciprocal Rank) | Posição do chunk "certo" no ranking de recuperação; valores mais altos indicam o documento relevante mais no topo. |

Use esta tabela para ver **efeito de tamanho na prática** (quem tem mediana maior em cada métrica), sem ainda falar em significância estatística.

---

## 2. `pvalues_<métrica>.{md,csv,tex}` — Significância entre pares

Há um arquivo por métrica, por exemplo:

- `pvalues_faithfulness.md`
- `pvalues_answer_relevancy.md`
- `pvalues_context_precision.md`
- `pvalues_context_recall.md`
- `pvalues_answer_correctness.md`
- `pvalues_mrr.md`

**O que é cada célula:** **p-value corrigido** pelo procedimento **Holm–Bonferroni** **dentro daquela métrica** (ajusta o fato de existirem várias comparações de pares de estratégias ao mesmo tempo).

- **Diagonal:** `—` (não há comparação de uma estratégia com ela mesma).
- **Asterisco `*`:** p-value corrigido **menor que α** (padrão **0,05** no script), ou seja, diferença **estatisticamente significativa** nesse teste e nível.
- **`n/d`:** não houve dado suficiente para aquela comparação (por exemplo, poucos pares válidos; o script usa `--min-pairs`, padrão 10).

**Como interpretar uma célula (linha A, coluna B):** é a comparação pareada entre as estratégias da linha e da coluna naquela métrica. A matriz é **simétrica**: o p-value de A vs B é o mesmo de B vs A (apenas espelhado).

**Importante:** significância **não** diz qual lado é "melhor" por si só; ela só indica que as distribuições pareadas diferem. Quem tem **mediana maior** naquele par é considerado "vencedor" no ranking (ver abaixo). Nos dados brutos (`all_comparisons.csv`) aparecem `median_a`, `median_b` e `winner`.

---

## 3. `ranking.{md,csv,tex}` — Contagem de vitórias

**Título:** "Ranking — Vitórias Significativas por Estratégia".

- Para cada célula (estratégia × métrica), o número é **quantas comparações** aquela estratégia **venceu** com **diferença significativa** (p corrigido menor que α **e** mediana superior à da outra estratégia no par).
- **Total Vitórias:** soma das vitórias da estratégia em todas as métricas.
- Linhas costumam vir **ordenadas** do maior total para o menor.

Estratégias com **0** em tudo não "perderam" necessariamente em tudo no descritivo; podem ter medianas parecidas ou diferenças **não** significativas após a correção.

---

## 4. `all_comparisons.csv` — Detalhe completo de cada par

Uma linha por **par de estratégias** × **métrica**. Colunas:

| Coluna | Significado |
|--------|-------------|
| `strategy_a`, `strategy_b` | Par comparado (ordem fixada pelo gerador; use medianas e `winner` para o desfecho). |
| `metric` | Métrica testada. |
| `n_pairs` | Número de perguntas com valor válido nas **duas** estratégias (base do Wilcoxon). |
| `median_a`, `median_b` | Medianas descritivas por estratégia naquele par e métrica. |
| `p_value` | p-value bruto do Wilcoxon. |
| `p_corrected_holm` | p-value após Holm–Bonferroni **naquela métrica** (é o que alimenta as tabelas `pvalues_*`). |
| `effect_size_r` | Correlação rank-biserial; magnitude do efeito (guia no código: valor absoluto abaixo de 0,1 trivial; 0,1–0,3 pequeno; 0,3–0,5 médio; acima de 0,5 grande). |
| `significant` | `True` se `p_corrected_holm` é menor que α. |
| `winner` | Estratégia com mediana maior **se** `significant`; caso contrário `—`. |

Este arquivo é o melhor lugar para auditar **por que** uma célula da matriz de p-values tem ou não `*`.

---

## 5. Parâmetros que mudam o que você vê

Ao rodar o script com filtros ou outros limiares, os arquivos refletem **só o subconjunto** analisado:

- `--doc-type pdf` ou `xml_lattes`: só perguntas daquele tipo de documento.
- `--question-type factual` ou `inferential`: só aquele tipo de pergunta.
- `--alpha` (padrão 0,05): limiar de significância após correção.
- `--min-pairs` (padrão 10): mínimo de pares para rodar o teste.

Com **menos de duas** estratégias concluídas no banco, o script pode salvar apenas o resumo (`summary`) e sair sem matrizes de p-value nem ranking.

---

## Leitura sugerida (ordem prática)

1. **`summary.md`** — panorama: medianas e dispersão por estratégia.
2. **`pvalues_*.md`** — onde as diferenças são estatisticamente sustentadas.
3. **`ranking.md`** — síntese: quem acumula mais vitórias significativas.
4. **`all_comparisons.csv`** — detalhe e tamanho de efeito quando precisar justificar uma afirmação.

Para a origem dos números e dos testes, veja `evaluation/run_analysis.py`, `evaluation/tables.py` e `evaluation/wilcoxon.py`.