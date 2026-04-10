# Avaliação Comparativa de Estratégias de Chunking para Currículos Lattes: um Framework Baseado em RAG e LLMs para Busca Semântica e Matchmaking Projeto–Pesquisador

**Disciplina:** Inteligência Artificial Generativa
**Professor:** Marcelo Rodrigo de Souza Pita
**Equipe 7:**
- Tiago Cardoso Soares
- Alan Tulio Lino Gonçalves

---

## 1. Introdução

### 1.1 Contextualização

A Retrieval-Augmented Generation (RAG) consolidou-se como a arquitetura de referência para sistemas de perguntas e respostas que combinam recuperação de documentos com geração de texto por Large Language Models (LLMs). Em um pipeline RAG típico, documentos extensos são segmentados em fragmentos menores — denominados chunks — que são indexados como vetores densos em um banco vetorial. Diante de uma consulta do usuário, os chunks semanticamente mais relevantes são recuperados e fornecidos como contexto ao modelo gerador, que produz uma resposta fundamentada nos trechos recuperados.

Nesse contexto, a etapa de chunking — a forma como o documento é dividido em fragmentos — desempenha papel central na qualidade do sistema. Chunks muito grandes diluem a informação relevante em meio a conteúdo irrelevante; chunks muito pequenos perdem contexto essencial para a compreensão. A escolha da estratégia de segmentação impacta diretamente a precisão da recuperação, a fidelidade da resposta gerada e, em última instância, a utilidade do sistema para o usuário final.

A administração pública brasileira produz e consome grandes volumes de documentos institucionais, como editais de fomento (EMBRAPII, FINEP, CNPq) e currículos acadêmicos na Plataforma Lattes. Esses documentos possuem estruturas heterogêneas: enquanto editais em PDF seguem prosa não-estruturada, os currículos Lattes são disponibilizados em formatos semi-estruturados (XML e JSON) com seções hierarquicamente definidas — artigos publicados, orientações concluídas, patentes registradas, formação acadêmica, entre outras. A aplicação de LLMs via RAG sobre esse corpus oferece oportunidades concretas para automação de processos de matchmaking entre projetos de fomento e pesquisadores, análise automatizada de produção científica e busca semântica inteligente em bases documentais extensas.

### 1.2 Motivação

Apesar da crescente adoção de sistemas RAG, a literatura ainda carece de avaliações sistemáticas e estatisticamente rigorosas sobre o impacto das estratégias de chunking na qualidade de sistemas de perguntas e respostas, especialmente quando aplicadas a documentos institucionais brasileiros em português. A maioria dos estudos adota abordagens genéricas (fixed-size ou recursive splitting) sem considerar a estrutura intrínseca dos documentos alvo.

No caso específico de currículos Lattes, a estrutura semi-estruturada em XML/JSON oferece uma oportunidade única: é possível projetar estratégias de chunking que respeitem a organização semântica do currículo — tratando cada produção científica, orientação ou patente como uma unidade atômica de informação. A hipótese é que essa abordagem structure-aware supere estratégias genéricas em tarefas de busca e geração sobre dados Lattes, preservando a integridade semântica de cada registro do pesquisador.

Adicionalmente, do ponto de vista da administração pública, a capacidade de localizar pesquisadores cujo perfil de produção científica esteja alinhado a editais de fomento — de forma automática, precisa e auditável — representa um avanço significativo em relação aos processos manuais de análise curricular atualmente praticados por agências de fomento e comitês de avaliação.

### 1.3 Objetivo

O objetivo deste trabalho é projetar, implementar e avaliar experimentalmente um framework baseado em RAG e LLMs que compare cinco estratégias de chunking aplicadas a documentos institucionais brasileiros — editais EMBRAPII em PDF e currículos Lattes em XML/JSON — respondendo à seguinte pergunta de pesquisa:

> **Como diferentes estratégias de chunking afetam a qualidade de recuperação e geração em documentos institucionais brasileiros?**

Especificamente, o trabalho busca:

1. Implementar cinco estratégias de chunking com graus variados de granularidade e aproveitamento da estrutura do documento.
2. Construir um pipeline RAG completo (ingestão, indexação vetorial, recuperação semântica e geração) parametrizável por estratégia de chunking.
3. Avaliar as estratégias de forma pareada, utilizando métricas do framework RAGAS e MRR, com análise estatística por teste de Wilcoxon signed-rank e correção de Holm-Bonferroni para comparações múltiplas.
4. Identificar qual estratégia oferece o melhor equilíbrio entre precisão de recuperação e qualidade de geração, com atenção especial ao comportamento em documentos semi-estruturados (Lattes).

---

## 2. Fundamentação Teórica

### 2.1 Arquiteturas de LLM Relacionadas

**Transformer e Modelos Generativos.** O GPT-4o-mini (OpenAI), utilizado neste trabalho como modelo gerador, pertence à família de modelos autorregressivos baseados na arquitetura Transformer (Vaswani et al., 2017). Modelos dessa família geram texto token a token, condicionando cada novo token ao contexto da sequência anterior. A variante GPT-4o-mini oferece desempenho competitivo com custo computacional reduzido, adequado para experimentos de larga escala com centenas de chamadas de API por estratégia avaliada.

**Modelos de Embedding.** O modelo text-embedding-3-small (OpenAI, 1536 dimensões) é empregado para converter chunks de texto e consultas em representações vetoriais densas. Esse modelo mapeia sequências de texto para um espaço vetorial de alta dimensionalidade onde a similaridade semântica é capturada pela distância cosseno entre vetores. Trata-se de um modelo encoder-only otimizado para tarefas de busca semântica, pertencente à classe de Sentence Embeddings que evoluiu a partir de modelos como Sentence-BERT (Reimers & Gurevych, 2019).

### 2.2 Técnicas Relacionadas

**Retrieval-Augmented Generation (RAG).** Proposta por Lewis et al. (2020), a RAG combina um componente de recuperação de documentos com um modelo de linguagem generativo. Em vez de depender exclusivamente do conhecimento internalizado nos parâmetros do modelo durante o pré-treinamento, o sistema recupera trechos relevantes de uma base de conhecimento externa e os fornece como contexto para a geração. Isso mitiga problemas como alucinações (geração de informações falsas) e desatualização do conhecimento.

**Chunking em Pipelines RAG.** O chunking é a etapa de pré-processamento que segmenta documentos em fragmentos indexáveis. As principais abordagens incluem:

- **Fixed-size:** divisão por janela deslizante de caracteres/tokens com overlap fixo — simples e determinístico, mas ignora fronteiras semânticas.
- **Recursive character splitting:** hierarquia de separadores (parágrafos, linhas, sentenças, palavras) que tenta preservar unidades maiores — amplamente adotado na biblioteca LangChain.
- **Sentence-based:** segmentação por sentenças linguísticas com agrupamento até um limite de tamanho — respeita fronteiras de frase, mas não a estrutura do documento.
- **Semantic chunking:** utiliza embeddings por sentença para detectar mudanças de tópico via quedas na similaridade cosseno entre sentenças adjacentes — captura fronteiras temáticas, mas com custo adicional de embedding na ingestão.
- **Structure-aware chunking:** explora a estrutura intrínseca do documento (tags XML, chaves JSON, headings) para gerar chunks que correspondam a unidades semânticas naturais do formato original.

**Framework RAGAS.** O RAGAS (Retrieval Augmented Generation Assessment) é um framework de avaliação automatizada que utiliza LLMs como juízes para pontuar a qualidade de sistemas RAG em múltiplas dimensões: Faithfulness (fidelidade ao contexto), Answer Relevancy (relevância da resposta), Context Precision (precisão do contexto recuperado), Context Recall (cobertura do contexto em relação à resposta de referência) e Answer Correctness (acurácia da resposta gerada).

**Teste de Wilcoxon Signed-Rank.** Teste não-paramétrico para amostras pareadas, adequado quando a distribuição dos dados não é normal — condição típica em métricas RAG que concentram valores nos extremos (0 e 1). No design deste experimento, cada pergunta é respondida por todas as estratégias, criando pares naturais para comparação.

### 2.3 Trabalhos e Soluções Relacionadas

Diversos trabalhos investigam o impacto do chunking em sistemas RAG, porém a maioria foca em corpus em inglês e documentos genéricos:

- **LangChain e LlamaIndex** oferecem implementações de splitting recursivo e por sentença como padrões de mercado, mas sem avaliação comparativa formal entre estratégias.
- **Estudos recentes de RAG evaluation** (e.g., benchmarks RAGAS, ARES, RECALL) propõem métricas automatizadas para avaliar pipelines, mas raramente controlam o chunking como variável independente isolada.
- **Aplicações de NLP em documentos brasileiros** concentram-se em classificação de texto ou sumarização, sendo escassas as avaliações de RAG sobre corpus institucional brasileiro (Lattes, editais de fomento).
- **Plataforma Lattes e mineração de dados:** trabalhos anteriores exploram a Plataforma Lattes para análise bibliométrica e formação de redes de colaboração, mas não a integram com pipelines de RAG para busca semântica.

O diferencial deste trabalho reside na combinação de: (i) cinco estratégias de chunking implementadas sobre o mesmo framework, (ii) corpus institucional brasileiro heterogêneo (PDF + XML/JSON), (iii) avaliação estatística pareada com controle rigoroso de variáveis e (iv) estratégia structure-aware específica para a estrutura do Currículo Lattes.

---

## 3. Caracterização do Problema

### 3.1 Problema da Administração Pública

Agências brasileiras de fomento à pesquisa — como EMBRAPII, CNPq, FINEP e CAPES — frequentemente precisam identificar pesquisadores cujo perfil acadêmico e de produção científica esteja alinhado a editais, projetos ou linhas temáticas específicas. Esse processo de matchmaking projeto–pesquisador atualmente é predominantemente manual: comitês de avaliação analisam centenas de currículos Lattes para identificar candidatos elegíveis, verificando publicações em áreas relevantes, orientações concluídas, patentes registradas e experiência em projetos anteriores.

Paralelamente, pesquisadores enfrentam dificuldade para localizar editais cujos requisitos coincidam com seu perfil de atuação. A assimetria de informação entre agências de fomento e pesquisadores resulta em subutilização de recursos, baixa taxa de aplicação em editais pertinentes e processos seletivos cujo escopo de candidatos não reflete o universo real de pesquisadores qualificados.

O volume de dados envolvido é substancial: a Plataforma Lattes possui mais de 7 milhões de currículos cadastrados, e agências como a EMBRAPII publicam dezenas de editais por ano, cada um com critérios específicos de elegibilidade, áreas temáticas e requisitos de experiência.

### 3.2 Partes Interessadas

| Parte Interessada | Interesse no Sistema |
|---|---|
| **Agências de fomento** (EMBRAPII, CNPq, FINEP) | Identificação automatizada de pesquisadores elegíveis para editais; redução do tempo de triagem de currículos |
| **Pesquisadores e grupos de pesquisa** | Busca semântica em editais compatíveis com seu perfil; respostas contextualizadas sobre requisitos de elegibilidade |
| **Comitês de avaliação** | Pré-triagem automatizada de candidatos; análise comparativa de perfis acadêmicos |
| **Gestores de CT&I** | Visão panorâmica da capacidade instalada (pesquisadores × áreas) para planejamento estratégico de fomento |
| **Comunidade acadêmica de IA** | Benchmark aberto para avaliação de estratégias de chunking em RAG sobre documentos institucionais brasileiros |

### 3.3 Critérios de Sucesso

O projeto define critérios de sucesso mensuráveis e estatisticamente verificáveis:

1. **Diferença estatisticamente significativa:** ao menos um par de estratégias de chunking deve apresentar diferença significativa (p < 0,05 após correção de Holm-Bonferroni) em pelo menos uma métrica de avaliação, demonstrando que a escolha do chunking não é trivial.
2. **Superioridade do structure-aware em dados Lattes:** a estratégia structure-aware deve vencer ao menos uma estratégia genérica em corpus de currículos Lattes, validando a hipótese de que o aproveitamento da estrutura do documento melhora a qualidade do RAG.
3. **Reprodutibilidade:** todos os experimentos devem ser reproduzíveis com seed fixo (temperature=0, seed=42), mesmas versões de modelo e infraestrutura conteinerizada.

---

## 4. Proposta de Solução

### 4.1 Diagrama de Arquitetura da Solução

A arquitetura do sistema segue o paradigma clássico de RAG com adaptações para suportar múltiplas estratégias de chunking e avaliação automatizada:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INFRAESTRUTURA (Docker Compose)              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  PostgreSQL   │    │    Qdrant     │    │   FastAPI (Python)   │  │
│  │    16-alpine  │    │ Vector Store │    │      3.12 + uv       │  │
│  │              │    │  1536 dims   │    │                      │  │
│  │  • Collections│    │  • Coleções   │    │  • API REST          │  │
│  │  • Documents  │    │    vetoriais  │    │  • Pipeline RAG      │  │
│  │  • Chunks     │    │  • Busca      │    │  • Avaliação RAGAS   │  │
│  │  • Experiments│    │    cosseno    │    │  • Experimentos      │  │
│  │  • Results    │    │              │    │                      │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
│         └───────────────────┼───────────────────────┘               │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   OpenAI API      │
                    │                   │
                    │ • text-embedding- │
                    │   3-small (embed) │
                    │ • gpt-4o-mini     │
                    │   (geração+eval)  │
                    └───────────────────┘
```

**Fluxo do Pipeline:**

```
   Documentos                    Consulta do
  (PDF/XML/JSON)                  Usuário
       │                            │
       ▼                            ▼
  ┌─────────┐                 ┌──────────┐
  │  Loader  │                │ Embedding │
  │(PyMuPDF, │                │  da Query │
  │lxml,JSON)│                └─────┬─────┘
  └────┬─────┘                      │
       ▼                            ▼
  ┌──────────┐               ┌───────────┐
  │ Chunking │               │  Qdrant   │
  │(5 estrat)│               │  Search   │
  └────┬─────┘               │ (top_k=5) │
       ▼                     └─────┬─────┘
  ┌──────────┐                     │
  │ Embedding │                    ▼
  │ dos Chunks│              ┌───────────┐
  └────┬─────┘               │ Contexto  │
       │                     │ Recuperado│
       ▼                     └─────┬─────┘
  ┌──────────┐                     │
  │  Qdrant  │                     ▼
  │  Upsert  │              ┌────────────┐
  └────┬─────┘              │  GPT-4o-   │
       │                    │   mini     │
       ▼                    │(temp=0,    │
  ┌──────────┐              │ seed=42)   │
  │PostgreSQL│              └─────┬──────┘
  │  Persist │                    │
  └──────────┘                    ▼
                            ┌───────────┐
                            │  Resposta  │
                            │  Gerada   │
                            └─────┬─────┘
                                  │
                                  ▼
                            ┌───────────┐
                            │  RAGAS +   │
                            │  MRR Eval  │
                            └───────────┘
```

### 4.2 Pipeline Desenvolvido

O pipeline do framework é composto por quatro estágios principais:

**Estágio 1 — Ingestão de Documentos.** Documentos são carregados por loaders especializados: PyMuPDF para PDFs, lxml para XMLs Lattes e parser JSON para currículos em formato JSON (conversão xmltodict). O texto extraído é então processado pela estratégia de chunking selecionada.

**Estágio 2 — Indexação Vetorial.** Cada chunk gerado é convertido em um vetor de 1536 dimensões pelo modelo text-embedding-3-small e armazenado no Qdrant. Simultaneamente, os metadados textuais (conteúdo, índice, estratégia, offsets) são persistidos no PostgreSQL para auditoria e análise posterior. O design impõe uma coleção por estratégia, isolando completamente o impacto de cada abordagem no índice vetorial.

**Estágio 3 — Recuperação e Geração.** Dada uma consulta, o sistema a converte em vetor (mesmo modelo de embedding), busca os top-k=5 chunks mais similares por distância cosseno no Qdrant e constrói o prompt de contexto para o GPT-4o-mini (temperature=0, seed=42), que gera a resposta final.

**Estágio 4 — Avaliação Automatizada.** O framework RAGAS avalia cada par (pergunta, resposta) em cinco métricas, utilizando o mesmo LLM como juiz. O MRR é calculado por heurística de janela de tokens, verificando se algum chunk recuperado contém subsequências da resposta de referência. Os resultados são armazenados no PostgreSQL por experimento e analisados offline com o teste de Wilcoxon signed-rank pareado e correção de Holm-Bonferroni.

**As cinco estratégias de chunking implementadas são:**

| Estratégia | Descrição | Caso de Uso |
|---|---|---|
| **Fixed-Size** | Janela deslizante de caracteres com overlap fixo | Baseline do experimento |
| **Recursive** | Hierarquia de separadores adaptada para português (parágrafos → linhas → sentenças → palavras) via LangChain | Abordagem padrão de mercado |
| **Sentence** | Segmentação por sentenças com proteção de abreviações em português (Dr., Prof., Art.) e overlap em nível de sentença | Respeito a fronteiras linguísticas |
| **Semantic** | Embeddings por sentença com detecção de quebras temáticas por queda de similaridade cosseno (percentil 25) | Fronteiras temáticas baseadas em semântica |
| **Structure-Aware** | Um chunk por unidade de produção científica (artigo, patente, orientação) via parsing de XML/JSON Lattes | Aproveitamento da estrutura do Currículo Lattes |

### 4.3 Principais Contribuições

1. **Framework open-source parametrizável** para avaliação comparativa de estratégias de chunking em RAG, conteinerizado com Docker Compose e reproduzível via API REST.
2. **Estratégia Structure-Aware para Currículos Lattes**, que trata cada produção científica como unidade atômica de chunking — contribuição específica para o domínio de documentos acadêmicos brasileiros.
3. **Adaptações para português** nas estratégias Recursive (hierarquia de separadores customizada) e Sentence (proteção de abreviações em pt-BR).
4. **Pipeline de avaliação estatística** com teste de Wilcoxon signed-rank pareado, correção de Holm-Bonferroni e reporte de tamanho de efeito (rank-biserial), indo além de simples comparações de médias.
5. **Golden set bilíngue e tipado**, com distinção entre perguntas factuais e inferenciais sobre dois tipos de documentos (editais PDF e currículos Lattes), permitindo análises estratificadas.

### 4.4 Riscos e Limitações

| Risco / Limitação | Mitigação / Observação |
|---|---|
| **Dependência de APIs OpenAI** | Modelos e preços podem mudar; experimentos reproduzíveis com seed=42 e temperature=0, mas variações menores entre chamadas são possíveis |
| **Custo do SemanticChunker** | Requer chamadas de embedding na ingestão (além do retrieval), gerando ~20.000 embeddings extras para 100 documentos |
| **MRR por heurística** | Sem anotações chunk-level, o MRR usa correspondência de janela de 5 tokens; pode subestimar relevância de chunks parafraseados |
| **Hybrid search incompleto** | A busca híbrida (BM25 + densa) está implementada como stub; atualmente funciona como fallback para busca semântica pura |
| **Golden set parcialmente anotado** | Perguntas sem expected_answer contribuem apenas para 3 das 5 métricas RAGAS (Faithfulness, Answer Relevancy, Context Precision) |
| **Especificidade do Structure-Aware** | Aplicável apenas a documentos Lattes em XML/JSON; para outros formatos, recorre a fallback recursivo |

---

## 5. Experimentos e Demonstração

### 5.1 Setup Experimental

**Dados:**
- Editais EMBRAPII em PDF (documentos institucionais de fomento à pesquisa)
- Currículos Lattes em JSON/XML (produção científica de pesquisadores)
- Golden set com perguntas factuais (fatos explícitos, critérios, requisitos) e inferenciais (síntese, interpretação, comparação)

**Modelos:**
- Embedding: text-embedding-3-small (OpenAI, 1536 dimensões)
- Gerador: GPT-4o-mini (temperature=0, seed=42)
- Avaliador RAGAS: GPT-4o-mini (temperature=0) — mesmo modelo do gerador para consistência

**Parâmetros controlados (variáveis fixas):**
- top_k = 5 (chunks recuperados por consulta)
- Retrieval: busca semântica por distância cosseno (vetor denso)
- Uma coleção Qdrant por estratégia (isolamento completo)
- Mesmas perguntas do golden set aplicadas a todas as estratégias (design pareado)

**Infraestrutura:**
- Docker Compose com três serviços: FastAPI (Python 3.12), PostgreSQL 16 e Qdrant
- Gerenciamento de dependências via uv

**Protocolo experimental:**
1. Criar uma coleção por estratégia de chunking
2. Ingerir o mesmo corpus de documentos em cada coleção com a respectiva estratégia
3. Executar o experimento com as mesmas golden questions em cada coleção
4. Coletar métricas RAGAS + MRR por pergunta por estratégia
5. Análise estatística offline: Wilcoxon pareado + Holm-Bonferroni

### 5.2 Resultados Alcançados

**Tabela 1 — Mediana (IQR) por Estratégia**

| Estratégia | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Answer Correctness | MRR |
|:---|:---|:---|:---|:---|:---|:---|
| Fixed-Size | 1,000 (0,317) | 0,691 (0,305) | 0,950 (0,244) | 1,000 (1,000) | 0,638 (0,555) | 0,000 (1,000) |
| Recursive | 1,000 (0,167) | 0,720 (0,272) | 0,917 (0,250) | 1,000 (1,000) | 0,651 (0,532) | 0,000 (1,000) |
| Semantic | 1,000 (0,200) | 0,729 (0,268) | 0,950 (0,250) | 1,000 (0,125) | 0,609 (0,508) | 0,000 (1,000) |
| Sentence | 1,000 (0,175) | 0,721 (0,269) | 1,000 (0,244) | 1,000 (0,000) | 0,679 (0,470) | 0,000 (1,000) |

*Formato: Mediana (IQR). IQR = Intervalo Interquartil (Q3 − Q1), medida de dispersão robusta a outliers.*

**Análise descritiva:** Todas as estratégias atingem mediana de 1,000 em Faithfulness, indicando que as respostas geradas são predominantemente fiéis ao contexto recuperado, independentemente do chunking. As diferenças se manifestam na dispersão (IQR): Fixed-Size apresenta o maior IQR (0,317), enquanto Recursive (0,167) e Sentence (0,175) são mais consistentes.

Em Answer Correctness, Sentence lidera com mediana 0,679, seguida de Recursive (0,651), Fixed-Size (0,638) e Semantic (0,609). Em Context Recall, Sentence alcança IQR de 0,000 — concentração máxima em torno da mediana 1,000 — sugerindo cobertura de contexto consistentemente alta.

**Tabela 2 — Comparações Estatisticamente Significativas (p < 0,05, Holm-Bonferroni)**

| Métrica | Par Comparado | p-value (corrigido) | Vencedor | Tamanho de Efeito (r) |
|:---|:---|:---|:---|:---|
| Faithfulness | Fixed-Size vs Recursive | 0,0149 | **Recursive** | 0,91 (grande) |
| Context Recall | Recursive vs Sentence | 0,0071 | **Sentence** | 0,98 (grande) |
| Answer Correctness | Semantic vs Sentence | 0,0015 | **Sentence** | 0,53 (grande) |

Das 36 comparações realizadas (6 pares × 6 métricas, considerando 4 estratégias), apenas três apresentaram diferença estatisticamente significativa após correção de Holm-Bonferroni. As três diferenças significativas apresentam tamanhos de efeito grandes (r > 0,5), indicando relevância prática além da significância estatística.

**Tabela 3 — Ranking de Vitórias Significativas por Estratégia**

| Estratégia | Answer Correctness | Answer Relevancy | Context Precision | Context Recall | Faithfulness | MRR | Total Vitórias |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sentence** | 1 | 0 | 0 | 1 | 0 | 0 | **2** |
| **Recursive** | 0 | 0 | 0 | 0 | 1 | 0 | **1** |
| Fixed-Size | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Semantic | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Interpretação dos resultados:**

A estratégia **Sentence** emerge como a mais competitiva no ranking geral, acumulando 2 vitórias significativas: superioridade em Context Recall (sobre Recursive) e em Answer Correctness (sobre Semantic). Isso sugere que o respeito a fronteiras de sentença — com proteção de abreviações em português — produz chunks que preservam melhor as unidades de significado necessárias para a recuperação e a geração de respostas corretas.

A estratégia **Recursive** obteve 1 vitória significativa em Faithfulness sobre Fixed-Size, indicando que a hierarquia de separadores reduz a ocorrência de chunks com cortes no meio de unidades semânticas, resultando em contextos mais fiéis para o gerador.

**Fixed-Size** e **Semantic** não obtiveram vitórias significativas. Para Fixed-Size, o resultado é esperado por tratar-se do baseline. Para Semantic, embora apresente medianas competitivas, a variabilidade dos scores impede que as diferenças atinjam significância estatística.

A métrica **MRR** apresenta mediana 0,000 para todas as estratégias, refletindo a natureza heurística da avaliação de relevância chunk-level (janela de 5 tokens da expected_answer), que pode subestimar chunks relevantes com respostas parafraseadas.

### 5.3 Impacto na Administração Pública

Os resultados demonstram que:

1. **A escolha do chunking não é trivial** — existem diferenças estatisticamente significativas entre estratégias, confirmando que essa decisão de engenharia impacta a qualidade do sistema RAG.

2. **Estratégias linguisticamente informadas (Sentence) superam abordagens genéricas** — particularmente em Answer Correctness e Context Recall, métricas diretamente ligadas à utilidade para o usuário final.

3. **O framework pode ser aplicado a cenários reais de matchmaking** — ao indexar currículos Lattes com a estratégia adequada e editais de fomento com estratégias genéricas otimizadas, agências de fomento podem automatizar a pré-triagem de candidatos com respostas fundamentadas e auditáveis.

4. **Auditabilidade completa** — cada resposta gerada é rastreável aos chunks recuperados, permitindo que avaliadores humanos verifiquem a fundamentação das recomendações do sistema.

---

## 6. Conclusão e Trabalhos Futuros

### 6.1 Revisão das Contribuições

Este trabalho apresentou um framework open-source para avaliação comparativa de estratégias de chunking em sistemas RAG aplicados a documentos institucionais brasileiros. As principais entregas incluem:

- Implementação de cinco estratégias de chunking (Fixed-Size, Recursive, Sentence, Semantic e Structure-Aware) em um pipeline RAG completo e conteinerizado.
- Adaptações específicas para português: separadores customizados no Recursive e proteção de abreviações pt-BR no Sentence.
- Estratégia Structure-Aware original para currículos Lattes, mapeando cada produção científica como unidade atômica de chunking.
- Pipeline de análise estatística com Wilcoxon signed-rank pareado, correção de Holm-Bonferroni e tamanho de efeito rank-biserial.
- API REST documentada (FastAPI + Swagger) para reprodução e extensão dos experimentos.

### 6.2 Discussão e Interpretação Crítica dos Resultados

Os resultados indicam que a estratégia **Sentence** oferece o melhor desempenho global entre as quatro estratégias avaliadas, com vitórias significativas em Context Recall e Answer Correctness. Essa superioridade pode ser atribuída à preservação de fronteiras de sentença, que mantém unidades semânticas completas nos chunks e facilita tanto a recuperação precisa quanto a geração de respostas corretas.

A estratégia **Recursive** demonstrou superioridade em Faithfulness sobre o baseline Fixed-Size, reforçando que a hierarquia de separadores reduz a fragmentação de contexto que prejudica a fidelidade das respostas.

A concentração de medianas em valores altos (Faithfulness e Context Recall frequentemente em 1,000) sugere um efeito de teto: o pipeline RAG com GPT-4o-mini já atinge desempenho elevado nessas métricas, tornando mais difícil a diferenciação entre estratégias. As diferenças significativas emergem justamente nas métricas com maior dispersão (Answer Correctness, com medianas entre 0,609 e 0,679), onde o impacto do chunking é mais perceptível.

É importante ressaltar que a ausência de vitórias significativas para uma estratégia não implica inferioridade prática — pode indicar que as diferenças são reais, mas insuficientes para significância estatística após a conservadora correção de Holm-Bonferroni.

### 6.3 Limitações

1. **Estratégia Structure-Aware não incluída nos resultados atuais** — os experimentos reportados avaliam quatro estratégias genéricas; a validação da hipótese de superioridade do Structure-Aware em dados Lattes permanece como trabalho futuro.
2. **MRR limitado por heurística** — a ausência de anotações de relevância chunk-level obriga o uso de matching por janela de tokens, subestimando chunks relevantes que expressam a resposta de forma parafraseada.
3. **Dependência de APIs comerciais** — embeddings e geração via OpenAI introduzem custo, latência e risco de mudanças na API.
4. **Busca híbrida como stub** — a recuperação BM25 + vetor denso está implementada como fallback para semântica pura.
5. **Ausência de filtragem por tipo de documento e tipo de pergunta nos resultados** — limitação técnica no join com o golden set impede análises estratificadas PDF vs. Lattes nesta versão.

### 6.4 Próximos Passos

1. **Avaliação completa do Structure-Aware** em corpus exclusivo de currículos Lattes, testando a hipótese de que chunks alinhados à estrutura do CV superam estratégias genéricas em perguntas sobre produção científica.
2. **Implementação de busca híbrida** (BM25 sparse + vetor denso) para avaliar o impacto da combinação de retrieval lexical e semântico.
3. **Expansão do golden set** com anotações de relevância chunk-level para cálculo de MRR e Recall@k sem heurísticas.
4. **Análises estratificadas** por tipo de documento (PDF vs. Lattes) e tipo de pergunta (factual vs. inferencial).
5. **Integração com modelos locais** (e.g., LLaMA, Gemma) para eliminar dependência de APIs comerciais e viabilizar implantação em ambientes de governo com restrições de dados.
6. **Interface de matchmaking** para uso por agências de fomento: dado um edital, recuperar e ranquear pesquisadores por aderência de perfil, com justificativa gerada pelo LLM rastreável aos chunks do currículo.

---

## Referências

- LEWIS, P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*, v. 33, 2020.
- VASWANI, A. et al. Attention Is All You Need. *Advances in Neural Information Processing Systems*, v. 30, 2017.
- REIMERS, N.; GUREVYCH, I. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *Proceedings of EMNLP-IJCNLP*, 2019.
- ES, S. et al. RAGAS: Automated Evaluation of Retrieval Augmented Generation. *arXiv preprint arXiv:2309.15217*, 2023.
- WILCOXON, F. Individual Comparisons by Ranking Methods. *Biometrics Bulletin*, v. 1, n. 6, p. 80–83, 1945.
- HOLM, S. A Simple Sequentially Rejective Multiple Test Procedure. *Scandinavian Journal of Statistics*, v. 6, n. 2, p. 65–70, 1979.
- COHEN, J. *Statistical Power Analysis for the Behavioral Sciences*. 2nd ed. Routledge, 1988.
- OPENAI. GPT-4o mini: Advancing Cost-Efficient Intelligence. 2024. Disponível em: https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/
- LANGCHAIN. Text Splitters Documentation. 2024. Disponível em: https://python.langchain.com/docs/concepts/text_splitters/
- CNPq. Plataforma Lattes. Disponível em: https://lattes.cnpq.br/
