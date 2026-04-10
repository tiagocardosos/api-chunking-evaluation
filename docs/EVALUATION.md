# Avaliação Estatística — Como Funciona

Este documento explica o pipeline de análise estatística implementado em `evaluation/`,
do carregamento dos resultados até a geração das tabelas do artigo.

---

## Visão geral do fluxo

```
PostgreSQL
    │
    ▼
results_loader.py          ← lê experimentos concluídos e organiza por estratégia
    │
    ▼
wilcoxon.py                ← testes pareados + correção múltipla
    │
    ▼
tables.py                  ← gera CSV / Markdown / LaTeX
    │
    ▼
evaluation/outputs/        ← arquivos salvos aqui (visíveis no host via volume)
```

Para rodar tudo de uma vez:

```bash
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
    uv run python evaluation/run_analysis.py
```

---

## Módulo 1 — `results_loader.py`

**Responsabilidade:** Conectar no PostgreSQL e retornar um dicionário
`{strategy_name → DataFrame}`, onde cada DataFrame tem uma linha por pergunta.

### Estrutura do DataFrame por estratégia

| Coluna               | Tipo    | Origem                        |
|----------------------|---------|-------------------------------|
| `faithfulness`       | float   | RAGAS                         |
| `answer_relevancy`   | float   | RAGAS                         |
| `context_precision`  | float   | RAGAS                         |
| `context_recall`     | float   | RAGAS                         |
| `answer_correctness` | float   | RAGAS (requer `expected_answer`) |
| `mrr`                | float   | heurística de janela de tokens |
| `question_type`      | str/None| `factual` ou `inferential`    |
| `doc_type`           | str/None| `pdf` ou `json_lattes`        |

O índice do DataFrame é o **texto da pergunta** — isso é o que permite o pareamento
no Wilcoxon (cada linha de uma estratégia é comparada com a linha da mesma pergunta
em outra estratégia).

### Por que o `question_type` e `doc_type` aparecem como `None`?

Esses campos não são armazenados na tabela `experiment_results` do PostgreSQL.
Atualmente o SQL retorna `NULL::text` para ambos. Para filtrar por tipo de
documento ou tipo de pergunta, o golden set precisaria incluir essas colunas
ou um join adicional com a tabela de documentos precisaria ser implementado.

---

## Módulo 2 — `wilcoxon.py`

**Responsabilidade:** Comparar pares de estratégias em cada métrica usando o
Wilcoxon Signed-Rank Test, depois aplicar correção de Holm-Bonferroni.

### Por que Wilcoxon e não t-test?

As métricas RAGAS (valores entre 0 e 1) raramente têm distribuição normal,
especialmente com amostras pequenas. O Wilcoxon é:
- Não-paramétrico: não assume normalidade
- Pareado: compara a mesma pergunta respondida por estratégias diferentes
- Mais poderoso que Mann-Whitney para dados pareados

### O que é o `min_pairs`?

Para que o teste seja estatisticamente válido, cada par de estratégias precisa
ter respondido as **mesmas perguntas** com scores válidos (sem NaN).
O parâmetro `min_pairs` (padrão: 10) define o mínimo de perguntas compartilhadas.

**Consequência prática:** se você rodou um experimento com `fixed_size` e 3 perguntas
e outro com `structure_aware` e 5 perguntas, mas só 2 perguntas são idênticas,
o par `fixed_size × structure_aware` é **ignorado** — não há dados pareados
suficientes para o teste.

Por isso o script mostra `Comparações totais: 0` com os experimentos de demonstração:
são estratégias com conjuntos de perguntas diferentes.

### Correção Holm-Bonferroni

Com 5 estratégias há C(5,2) = 10 pares por métrica = 60 testes no total.
Rodar 60 testes com α=0.05 inflacionaria fortemente a taxa de falso positivo.
A correção de Holm-Bonferroni:

1. Ordena os p-values em ordem crescente: p₁ ≤ p₂ ≤ ... ≤ pₘ
2. Para cada k: `p_corrected[k] = p[k] × (m − k + 1)`
3. Rejeita H₀ até encontrar o primeiro não-rejeito

É mais poderosa que a correção de Bonferroni simples (que multiplicaria todos
por m), pois aplica um multiplicador menor para os testes mais significativos.

### Tamanho de efeito (r)

O tamanho de efeito usa a correlação rank-biserial:

```
r = 1 − (2W) / (n × (n+1) / 2)
```

onde W é a estatística do Wilcoxon (soma dos ranks menores). Interpretação:
- `|r| < 0.1` → efeito trivial
- `0.1–0.3`  → efeito pequeno
- `0.3–0.5`  → efeito médio
- `> 0.5`    → efeito grande

---

## Módulo 3 — `tables.py`

**Responsabilidade:** Converter os resultados em tabelas prontas para o artigo.

### Tabelas geradas

| Arquivo                    | Conteúdo                                                    |
|----------------------------|-------------------------------------------------------------|
| `summary.{csv,md,tex}`     | Mediana ± IQR de cada métrica × estratégia                  |
| `pvalues_<metrica>.{...}`  | Matriz de p-values corrigidos para cada métrica             |
| `ranking.{csv,md,tex}`     | Número de vitórias significativas por estratégia            |
| `all_comparisons.csv`      | Dados brutos: todos os pares, p-values, efeitos, vencedores |

### Formato das células da `summary_table`

```
0.732 (0.156)
 ↑       ↑
Mediana  IQR (Q3 − Q1)
```

O IQR (Interquartile Range) é preferido ao desvio padrão para distribuições
não-normais — mede a dispersão dos 50% centrais.

### Por que "ranking" só aparece com comparações?

A tabela de ranking conta vitórias em comparações **estatisticamente significativas**.
Se o Wilcoxon não rodou (por falta de `min_pairs`), não há vitórias para contar
e o arquivo é omitido com `[SKIP]`.

---

## Saídas — onde ficam os arquivos

Os arquivos são salvos em `evaluation/outputs/` (no host, via volume Docker):

```
evaluation/
  outputs/
    summary.csv
    summary.md
    summary.tex
    pvalues_faithfulness.{csv,md,tex}
    pvalues_answer_relevancy.{csv,md,tex}
    ...
    ranking.{csv,md,tex}          ← só se houver comparações
    all_comparisons.csv           ← só se houver comparações
```

---

## Critérios de sucesso (EXPERIMENT-SPEC §7)

O script imprime automaticamente:

| Critério | Condição                                                              |
|----------|-----------------------------------------------------------------------|
| 1        | Pelo menos 1 par com diferença estatisticamente significativa         |
| 2        | `structure_aware` vence em pelo menos uma métrica para corpus Lattes  |

Para atingir o Critério 1, o golden set precisa ter **≥ 10 perguntas idênticas**
executadas em pelo menos 2 estratégias.

---

## Filtros disponíveis

```bash
# Só PDFs
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
    uv run python evaluation/run_analysis.py --doc-type pdf

# Só perguntas inferenciais
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
    uv run python evaluation/run_analysis.py --question-type inferential

# Diretório de saída customizado
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
    uv run python evaluation/run_analysis.py --output-dir evaluation/outputs/lattes

# Reduzir min_pairs para testes (não recomendado para o artigo)
docker exec rag-chunking-evaluation-mestrado-fastapi-1 \
    uv run python evaluation/run_analysis.py --min-pairs 3
```

---

## O que falta para o experimento real

O estado atual (demo com 23 Lattes, structure_aware, 5–6 perguntas) é insuficiente
para análise estatística por dois motivos:

1. **Poucas estratégias:** só `fixed_size` e `structure_aware` têm dados. Faltam
   `recursive`, `sentence` e `semantic`.

2. **Poucas perguntas pareadas:** os dois experimentos não compartilham as mesmas
   perguntas, então não há pares válidos para o Wilcoxon.

O plano correto é:
1. Definir o **golden set definitivo** com ≥ 10 perguntas idênticas
2. Rodar um experimento com cada uma das 5 estratégias usando as mesmas perguntas
3. Executar `run_analysis.py` — aí o Wilcoxon terá dados suficientes
