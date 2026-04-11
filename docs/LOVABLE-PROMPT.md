# Prompt para Criação do Frontend — Lovable

## Contexto do Projeto

Este é o frontend de um **sistema de avaliação comparativa de estratégias de chunking em RAG (Retrieval-Augmented Generation)** para documentos institucionais brasileiros. O sistema compara cinco estratégias de chunking (Fixed-Size, Recursive, Sentence, Semantic e Structure-Aware) aplicadas a documentos normativos da EMBRAPII (PDFs) e currículos Lattes (XML/JSON), utilizando métricas automatizadas do RAGAS e análise estatística com teste de Wilcoxon.

O backend já existe como uma API REST (FastAPI). **Este frontend NÃO deve fazer integração real com o backend** — use dados mockados estáticos para simular todas as telas. A integração virá depois.

---

## Direção Visual e Identidade

### Tema principal: "Matrix Acadêmico"
- **Fundo escuro** predominante (preto, cinza grafite #1a1a2e, #16213e)
- **Paleta primária:** verde neon (#00ff41, #39ff14), verde escuro (#0d7377, #00b894)
- **Paleta secundária:** cinza grafite (#2d3436, #636e72), branco (#dfe6e9, #ffeaa7 para destaques)
- **Accent:** toques de azul elétrico (#0984e3) para links e ações secundárias
- Tipografia moderna: Inter ou JetBrains Mono para elementos de código/terminal
- Cards com bordas sutis em verde neon com glow sutil (box-shadow com verde)
- Backgrounds com padrões sutis: grid digital, dots pattern, ou linhas de circuito com opacidade baixa (~5%)
- Sensação geral: **inteligente, técnico, limpo, premium** — como um dashboard de pesquisa em IA
- Evitar excesso visual — cada elemento deve ter propósito
- Glassmorphism sutil em cards e modais (backdrop-blur com fundo semi-transparente)

### Componentes visuais recorrentes:
- Status badges com glow (pending = amarelo, running = verde pulsante, completed = verde sólido, failed = vermelho)
- Tabelas com hover highlight em verde neon sutil
- Gráficos com tema dark e linhas/barras em verde neon
- Code blocks e previews com estilo terminal (fundo #0a0a0a, texto verde, font mono)
- Breadcrumbs com separador "›" estilizado
- Sidebar retrátil com ícones phosphor ou lucide

---

## Estrutura de Páginas e Navegação

### Layout Principal
- **Sidebar esquerda** fixa, retrátil, com logo do projeto no topo ("RAG Chunking Lab" ou similar com ícone de rede neural)
- **Header top** com breadcrumb + nome da página atual + ícone de tema (dark/light toggle apenas visual)
- **Área de conteúdo** principal responsiva

### Menu da Sidebar (itens e ícones sugeridos):

1. **Dashboard** (ícone: LayoutDashboard) — visão geral
2. **Coleções** (ícone: FolderOpen) — CRUD de coleções
3. **Documentos** (ícone: FileText) — upload e ingestão
4. **Chunking Lab** (ícone: Scissors) — preview de estratégias
5. **Busca Semântica** (ícone: Search) — busca vetorial
6. **RAG Chat** (ícone: MessageSquare) — perguntas e respostas
7. **Experimentos** (ícone: FlaskConical) — rodar e monitorar
8. **Resultados** (ícone: BarChart3) — análise e visualização
9. **Golden Set** (ícone: Star) — gerenciamento de perguntas

---

## Página 1: Dashboard

### Descrição
Visão geral do sistema com métricas resumidas e acesso rápido às funcionalidades principais.

### Componentes:
- **4 cards de estatísticas** no topo em grid:
  - Total de Coleções (ícone: FolderOpen, valor mock: 5)
  - Total de Documentos Ingeridos (ícone: FileText, valor mock: 8)
  - Experimentos Concluídos (ícone: FlaskConical, valor mock: 4)
  - Golden Questions (ícone: Star, valor mock: 231)

- **Card "Últimos Experimentos"**: tabela compacta com 3-4 linhas mostrando:
  - Nome do experimento
  - Estratégia de chunking (badge colorido)
  - Status (badge com glow)
  - Answer Correctness (mediana)
  - Data

- **Card "Comparação Rápida"**: mini gráfico radar ou barchart comparando medianas das 4 estratégias em Answer Correctness

- **Card "Ações Rápidas"**: 3 botões grandes com ícones:
  - "Nova Ingestão" → vai para /documentos
  - "Rodar Experimento" → vai para /experimentos
  - "Ver Resultados" → vai para /resultados

### Dados mock do dashboard:
```json
{
  "collections": 5,
  "documents": 8,
  "experiments_completed": 4,
  "golden_questions": 231,
  "recent_experiments": [
    {"name": "Exp Fixed-Size 512", "strategy": "fixed_size", "status": "completed", "avg_answer_correctness": 0.638, "created_at": "2025-03-15"},
    {"name": "Exp Recursive 512", "strategy": "recursive", "status": "completed", "avg_answer_correctness": 0.651, "created_at": "2025-03-16"},
    {"name": "Exp Sentence 512", "strategy": "sentence", "status": "completed", "avg_answer_correctness": 0.679, "created_at": "2025-03-17"},
    {"name": "Exp Semantic 512", "strategy": "semantic", "status": "running", "avg_answer_correctness": null, "created_at": "2025-03-18"}
  ]
}
```

---

## Página 2: Coleções

### Descrição
CRUD de coleções vetoriais. Cada coleção agrupa documentos ingeridos com uma única estratégia de chunking.

### Componentes:
- **Botão "Nova Coleção"** no header da página → abre modal
- **Grid de cards** (3 colunas) representando coleções, cada uma com:
  - Nome da coleção
  - Descrição (ou "Sem descrição")
  - Data de criação
  - Contagem de documentos na coleção
  - Botão "Ver Documentos" (→ filtra página de documentos)
  - Botão "Deletar" com confirmação

- **Modal "Nova Coleção"**:
  - Campo: Nome (obrigatório)
  - Campo: Descrição (opcional, textarea)
  - Botões: Cancelar / Criar

### Dados mock:
```json
[
  {"id": "col-001", "name": "EMBRAPII Fixed-Size", "description": "Documentos EMBRAPII com chunking fixed-size 512/50", "created_at": "2025-03-10", "document_count": 3},
  {"id": "col-002", "name": "EMBRAPII Recursive", "description": "Documentos EMBRAPII com chunking recursive 512/50", "created_at": "2025-03-11", "document_count": 3},
  {"id": "col-003", "name": "EMBRAPII Sentence", "description": "Documentos EMBRAPII com chunking sentence 512", "created_at": "2025-03-12", "document_count": 3},
  {"id": "col-004", "name": "EMBRAPII Semantic", "description": "Documentos EMBRAPII com chunking semantic p25", "created_at": "2025-03-13", "document_count": 3},
  {"id": "col-005", "name": "Lattes Structure-Aware", "description": "Currículos Lattes com structure-aware chunking", "created_at": "2025-03-14", "document_count": 23}
]
```

---

## Página 3: Documentos

### Descrição
Upload de documentos e ingestão com escolha de estratégia de chunking. Mostra documentos já ingeridos e permite ver os chunks gerados.

### Componentes:

**Seção superior — Upload e Ingestão:**
- Área de drag-and-drop para upload de arquivo (aceita .pdf, .xml, .json)
- Select: Coleção de destino (lista das coleções existentes)
- Select: Estratégia de Chunking (enum: fixed_size, recursive, sentence, semantic, structure_aware)
- Se fixed_size ou recursive:
  - Input number: Chunk Size (default 512, min 64, max 2048)
  - Input number: Chunk Overlap (default 50, min 0, max 512)
- Se sentence:
  - Input number: Max Chunk Size (default 512)
  - Input number: Overlap Sentences (default 1)
- Se semantic:
  - Input number: Breakpoint Percentile (default 25, min 0, max 100)
  - Input number: Max Chunk Size (default 1024)
- Se structure_aware:
  - Input number: Max Chunk Size (default 1024)
  - Texto informativo: "Ideal para currículos Lattes (XML/JSON)"
- Botão: "Ingerir Documento"

**Seção inferior — Documentos Ingeridos:**
- Tabela com colunas:
  - Arquivo (nome)
  - Tipo (badge: PDF / XML Lattes / JSON Lattes)
  - Coleção
  - Estratégia (badge colorido)
  - Chunks gerados (número)
  - Data de ingestão
  - Ação: "Ver Chunks" → expande ou abre modal

**Modal/Painel "Chunks do Documento":**
- Título: "Chunks de {filename}"
- Info: "{total_chunks} chunks | Estratégia: {strategy}"
- Lista scrollável de chunks, cada um como card estilo terminal:
  - Header: "Chunk #{index}" + metadata badges
  - Body: conteúdo do chunk em fonte mono, com max-height e scroll
  - Cor de fundo: #0a0a0a, texto: #00ff41

### Dados mock de documentos:
```json
[
  {"id": "doc-001", "filename": "manual_operacao_embrapii_v6.pdf", "doc_type": "pdf", "collection": "EMBRAPII Fixed-Size", "strategy": "fixed_size", "total_chunks": 245, "created_at": "2025-03-10"},
  {"id": "doc-002", "filename": "codigo_etica_agosto_2019.pdf", "doc_type": "pdf", "collection": "EMBRAPII Fixed-Size", "strategy": "fixed_size", "total_chunks": 68, "created_at": "2025-03-10"},
  {"id": "doc-003", "filename": "regimento_comite_etica.pdf", "doc_type": "pdf", "collection": "EMBRAPII Fixed-Size", "strategy": "fixed_size", "total_chunks": 92, "created_at": "2025-03-10"},
  {"id": "doc-004", "filename": "2429856261320761.json", "doc_type": "json_lattes", "collection": "Lattes Structure-Aware", "strategy": "structure_aware", "total_chunks": 47, "created_at": "2025-03-14"}
]
```

### Dados mock de chunks (para preview):
```json
[
  {"chunk_index": 0, "content": "MANUAL DE OPERAÇÃO EMBRAPII\n\n1. INTRODUÇÃO\n\n1.1 Objetivo\nEste Manual de Operação tem por objetivo estabelecer as normas, procedimentos e critérios operacionais para o funcionamento da EMBRAPII...", "metadata": {"strategy": "fixed_size", "char_start": 0, "char_end": 512}},
  {"chunk_index": 1, "content": "...credenciamento de Unidades EMBRAPII. As Unidades credenciadas devem atender aos requisitos mínimos de infraestrutura, equipe técnica qualificada e capacidade de execução de projetos de PD&I...", "metadata": {"strategy": "fixed_size", "char_start": 462, "char_end": 974}},
  {"chunk_index": 2, "content": "1.2 Abrangência\nO presente Manual se aplica a todas as Unidades EMBRAPII credenciadas, em processo de credenciamento, e às empresas parceiras que desenvolvam projetos no âmbito do modelo EMBRAPII...", "metadata": {"strategy": "fixed_size", "char_start": 924, "char_end": 1436}}
]
```

---

## Página 4: Chunking Lab

### Descrição
Permite fazer upload de um documento e visualizar lado a lado como diferentes estratégias o dividem em chunks, sem ingerir no banco.

### Componentes:
- **Upload zone** para arquivo
- **Grid de seleção** das 5 estratégias (checkboxes com ícones, pode selecionar múltiplas)
- Parâmetros ajustáveis conforme estratégia selecionada (mesmos da página de documentos)
- Botão "Gerar Preview"
- **Área de resultado**: painel comparativo lado a lado (até 2-3 estratégias visíveis simultaneamente, com tabs para alternar se mais)
  - Cada coluna/tab mostra:
    - Nome da estratégia
    - Total de chunks
    - Média de caracteres por chunk
    - Lista de chunks estilo terminal

- **Card de estatísticas comparativas** abaixo:
  - Tabela: Estratégia | Total Chunks | Média chars/chunk | Min | Max | Mediana

### Dados mock:
```json
{
  "fixed_size": {"total_chunks": 245, "avg_size": 498, "min_size": 312, "max_size": 512, "median_size": 510},
  "recursive": {"total_chunks": 198, "avg_size": 623, "min_size": 89, "max_size": 1024, "median_size": 587},
  "sentence": {"total_chunks": 178, "avg_size": 689, "min_size": 45, "max_size": 1156, "median_size": 645},
  "semantic": {"total_chunks": 142, "avg_size": 867, "min_size": 123, "max_size": 2048, "median_size": 812}
}
```

---

## Página 5: Busca Semântica

### Descrição
Interface para realizar buscas semânticas nas coleções indexadas.

### Componentes:
- **Barra de busca** grande e destacada com placeholder "Faça uma pergunta sobre os documentos..."
- Select: Coleção (obrigatório)
- Select: Estratégia de Busca (semantic / hybrid) — default: semantic
- Input number: top_k (default 5, min 1, max 20)
- Botão "Buscar"

- **Área de resultados**: lista de cards de resultados, cada um com:
  - Badge de posição (#1, #2, ...) com destaque no primeiro
  - Score de similaridade (barra de progresso verde + número)
  - Conteúdo do chunk (texto com highlight nos termos buscados, se possível)
  - Metadata do chunk (estratégia, documento de origem, etc.)

### Dados mock:
```json
{
  "query": "Quais são os requisitos para credenciamento de unidades EMBRAPII?",
  "results": [
    {"rank": 1, "score": 0.92, "content": "Os requisitos mínimos para credenciamento de Unidades EMBRAPII incluem: infraestrutura laboratorial adequada, equipe técnica qualificada com experiência em PD&I, capacidade comprovada de captação de projetos com empresas...", "metadata": {"document": "manual_operacao_embrapii_v6.pdf", "strategy": "sentence", "chunk_index": 34}},
    {"rank": 2, "score": 0.87, "content": "O processo de credenciamento envolve a submissão de proposta pela instituição candidata, análise documental, visita técnica in loco e deliberação pelo Conselho Deliberativo da EMBRAPII...", "metadata": {"document": "manual_operacao_embrapii_v6.pdf", "strategy": "sentence", "chunk_index": 35}},
    {"rank": 3, "score": 0.81, "content": "As Unidades credenciadas devem manter atualizado o Plano de Ação Institucional, contendo metas de projetos, indicadores de desempenho e planejamento de investimentos em infraestrutura...", "metadata": {"document": "manual_operacao_embrapii_v6.pdf", "strategy": "sentence", "chunk_index": 42}},
    {"rank": 4, "score": 0.76, "content": "A EMBRAPII poderá suspender ou descredenciar Unidades que não cumprirem as metas estabelecidas no Plano de Ação ou que descumprirem as normas do Manual de Operação...", "metadata": {"document": "manual_operacao_embrapii_v6.pdf", "strategy": "sentence", "chunk_index": 67}},
    {"rank": 5, "score": 0.71, "content": "O credenciamento tem vigência de até 6 anos, podendo ser renovado mediante avaliação de desempenho e cumprimento dos requisitos estabelecidos...", "metadata": {"document": "manual_operacao_embrapii_v6.pdf", "strategy": "sentence", "chunk_index": 36}}
  ]
}
```

---

## Página 6: RAG Chat

### Descrição
Interface de chat estilo ChatGPT para perguntas e respostas com RAG, mostrando contexto recuperado e latência.

### Componentes:
- **Sidebar de configuração** (colapsável, à direita):
  - Select: Coleção
  - Select: Estratégia de Busca (semantic/hybrid)
  - Input number: top_k
  - Select: Modelo gerador (default: gpt-4o-mini)

- **Área de chat** principal:
  - Histórico de mensagens (user/assistant) com bolhas estilizadas
  - Mensagem do assistente inclui:
    - Texto da resposta
    - Seção expansível "Contexto Recuperado" com os chunks usados (estilo accordion)
    - Badge com latência ("342ms")
  - Input na parte inferior com botão enviar

### Dados mock (conversa exemplo):
```json
[
  {
    "role": "user",
    "content": "Qual é o prazo máximo para prestação de contas de projetos EMBRAPII?"
  },
  {
    "role": "assistant",
    "content": "De acordo com o Manual de Operação EMBRAPII, o prazo máximo para prestação de contas de projetos é de **90 dias** após a conclusão do projeto. A Unidade EMBRAPII deve apresentar o relatório técnico final e a prestação de contas financeira dentro desse período, sob pena de suspensão de novos desembolsos.",
    "context": [
      {"rank": 1, "score": 0.94, "content": "A prestação de contas de cada projeto deve ser apresentada pela Unidade EMBRAPII no prazo máximo de 90 (noventa) dias após a data de conclusão do projeto...", "source": "manual_operacao_embrapii_v6.pdf"},
      {"rank": 2, "score": 0.88, "content": "O descumprimento dos prazos de prestação de contas poderá acarretar a suspensão de novos desembolsos...", "source": "manual_operacao_embrapii_v6.pdf"}
    ],
    "latency_ms": 342
  }
]
```

---

## Página 7: Experimentos

### Descrição
Configuração, execução e monitoramento de experimentos de avaliação.

### Componentes:

**Aba "Novo Experimento":**
- Campo: Nome do Experimento
- Select: Coleção
- Select: Estratégia de Chunking (informativo — mostra qual estratégia a coleção usa)
- Input: Chunk Size (default 512)
- Input: Chunk Overlap (default 50)
- Select: Modelo de Embedding (default: text-embedding-3-small)
- Select: Modelo Gerador (default: gpt-4o-mini)
- Select: Estratégia de Busca (semantic/hybrid)
- Input: top_k (default 5)
- **Seção Golden Questions:**
  - Upload de arquivo JSON com golden questions
  - OU textarea para colar JSON
  - Preview: tabela com as primeiras 5 perguntas carregadas
  - Contagem total: "231 perguntas carregadas (139 factual, 92 inferential)"
- Botão: "Iniciar Experimento"

**Aba "Meus Experimentos":**
- Tabela de experimentos com colunas:
  - Nome
  - Coleção
  - Estratégia (badge)
  - Status (badge com glow animado para "running")
  - Total de perguntas
  - Méd. Answer Correctness
  - Méd. Faithfulness
  - Data
  - Ação: "Ver Detalhes"

### Dados mock de experimentos:
```json
[
  {
    "id": "exp-001",
    "name": "Fixed-Size 512/50 EMBRAPII",
    "collection": "EMBRAPII Fixed-Size",
    "strategy": "fixed_size",
    "status": "completed",
    "total_questions": 231,
    "avg_faithfulness": 0.847,
    "avg_answer_relevancy": 0.691,
    "avg_context_precision": 0.876,
    "avg_context_recall": 0.723,
    "avg_answer_correctness": 0.638,
    "created_at": "2025-03-15"
  },
  {
    "id": "exp-002",
    "name": "Recursive 512/50 EMBRAPII",
    "collection": "EMBRAPII Recursive",
    "strategy": "recursive",
    "status": "completed",
    "total_questions": 231,
    "avg_faithfulness": 0.891,
    "avg_answer_relevancy": 0.720,
    "avg_context_precision": 0.854,
    "avg_context_recall": 0.756,
    "avg_answer_correctness": 0.651,
    "created_at": "2025-03-16"
  },
  {
    "id": "exp-003",
    "name": "Sentence 512 EMBRAPII",
    "collection": "EMBRAPII Sentence",
    "strategy": "sentence",
    "status": "completed",
    "total_questions": 231,
    "avg_faithfulness": 0.878,
    "avg_answer_relevancy": 0.721,
    "avg_context_precision": 0.893,
    "avg_context_recall": 0.812,
    "avg_answer_correctness": 0.679,
    "created_at": "2025-03-17"
  },
  {
    "id": "exp-004",
    "name": "Semantic p25 EMBRAPII",
    "collection": "EMBRAPII Semantic",
    "strategy": "semantic",
    "status": "completed",
    "total_questions": 231,
    "avg_faithfulness": 0.862,
    "avg_answer_relevancy": 0.729,
    "avg_context_precision": 0.867,
    "avg_context_recall": 0.789,
    "avg_answer_correctness": 0.609,
    "created_at": "2025-03-18"
  }
]
```

---

## Página 8: Resultados e Análise (MAIS IMPORTANTE)

### Descrição
Dashboard analítico com visualizações dos resultados dos experimentos. Esta é a página mais rica visualmente.

### Componentes:

**Seção 1 — Seletor de Experimentos:**
- Multi-select para escolher quais experimentos comparar (até 5)
- Botão "Comparar Selecionados"

**Seção 2 — Tabela Resumo (Mediana + IQR):**
Tabela estilizada (estilo heatmap com intensidade de cor) mostrando:

| Estratégia | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Answer Correctness | MRR |
|:---|:---|:---|:---|:---|:---|:---|
| Fixed-Size | 1.000 (0.317) | 0.691 (0.305) | 0.950 (0.244) | 1.000 (1.000) | 0.638 (0.555) | 0.000 (1.000) |
| Recursive | 1.000 (0.167) | 0.720 (0.272) | 0.917 (0.250) | 1.000 (1.000) | 0.651 (0.532) | 0.000 (1.000) |
| Semantic | 1.000 (0.200) | 0.729 (0.268) | 0.950 (0.250) | 1.000 (0.125) | 0.609 (0.508) | 0.000 (1.000) |
| Sentence | 1.000 (0.175) | 0.721 (0.269) | 1.000 (0.244) | 1.000 (0.000) | 0.679 (0.470) | 0.000 (1.000) |

- Células com valor mais alto na coluna recebem fundo verde mais intenso
- Formato: "Mediana (IQR)" 
- Tooltip explicando IQR ao passar o mouse no header

**Seção 3 — Gráfico Radar:**
- Gráfico radar (spider chart) com as 6 métricas nos eixos
- Uma linha por estratégia com cor distinta
- Legenda clicável para toggle de visibilidade

**Seção 4 — Box Plots por Métrica:**
- 6 gráficos box plot (um por métrica)
- Cada box plot mostra a distribuição das 4 estratégias lado a lado
- Cores consistentes por estratégia
- Layout: grid 2x3

**Seção 5 — Comparações Estatísticas (Wilcoxon):**
Card com título "Comparações Estatisticamente Significativas (p < 0.05, Holm-Bonferroni)"

Tabela destacada:

| Métrica | Par Comparado | p-value (corrigido) | Vencedor | Tamanho de Efeito (r) |
|:---|:---|:---|:---|:---|
| Faithfulness | Fixed-Size vs Recursive | 0.0149 | **Recursive** | 0.91 (grande) |
| Context Recall | Recursive vs Sentence | 0.0071 | **Sentence** | 0.98 (grande) |
| Answer Correctness | Semantic vs Sentence | 0.0015 | **Sentence** | 0.53 (grande) |

- Linha do vencedor em verde neon
- Badge do tamanho de efeito com cor (grande = verde, médio = amarelo, pequeno = cinza)

**Seção 6 — Ranking de Vitórias:**
Tabela estilizada como "placar":

| Estratégia | Vitórias | 🏆 |
|:---|:---:|:---|
| **Sentence** | 2 | Context Recall, Answer Correctness |
| **Recursive** | 1 | Faithfulness |
| Fixed-Size | 0 | — |
| Semantic | 0 | — |

- A estratégia líder recebe destaque visual especial (borda verde, ícone de troféu)

**Seção 7 — Gráfico de Barras Agrupadas:**
- Eixo X: métricas
- Barras agrupadas por estratégia
- Valores medianos

**Seção 8 — Detalhes por Pergunta (expansível):**
- Tabela paginada (20 por página) com resultados por pergunta:
  - Pergunta (texto truncado com tooltip)
  - Tipo (factual/inferential badge)
  - Score de cada estratégia (mini barras horizontais)
- Filtros: por tipo de pergunta, por documento

---

## Página 9: Golden Set

### Descrição
Gerenciamento e visualização do golden set de perguntas.

### Componentes:
- **Card de estatísticas:**
  - Total de perguntas: 231
  - Factuais: 139 (60%)
  - Inferenciais: 92 (40%)
  - Com expected_answer: 231
  - Donut chart: distribuição por tipo

- **Card por documento:**
  - Regimento Comitê de Conduta Ética: 46 perguntas (30 factual, 16 inferential)
  - Código de Ética: 35 perguntas (16 factual, 19 inferential)
  - Manual de Operação v6: 150 perguntas (93 factual, 57 inferential)
  - Bar chart horizontal mostrando proporção factual vs inferential

- **Tabela completa:**
  - Colunas: #, Pergunta, Tipo (badge), Documento, Expected Answer (truncado)
  - Filtro por tipo e por documento
  - Busca textual na pergunta
  - Paginação

- **Upload de Golden Set:**
  - Área de upload JSON
  - Validação visual: mostra erros se formato inválido
  - Preview das primeiras 5 perguntas após upload

### Dados mock (amostra):
```json
[
  {"id": 1, "question": "Qual o prazo máximo para credenciamento?", "type": "factual", "document": "Manual de Operação EMBRAPII v6", "expected_answer": "O prazo máximo para credenciamento de Unidades EMBRAPII é de 6 anos..."},
  {"id": 2, "question": "Quais são as penalidades previstas para descumprimento do código de ética?", "type": "factual", "document": "Código de Ética ago/2019", "expected_answer": "As penalidades incluem advertência, suspensão..."},
  {"id": 3, "question": "Como a evolução do modelo EMBRAPII impacta a sustentabilidade das unidades credenciadas?", "type": "inferential", "document": "Manual de Operação EMBRAPII v6", "expected_answer": "A evolução do modelo tende a fortalecer..."},
  {"id": 4, "question": "Qual a composição do Comitê de Conduta Ética?", "type": "factual", "document": "Regimento Comitê de Conduta Ética", "expected_answer": "O Comitê é composto por 5 membros..."},
  {"id": 5, "question": "De que forma o processo de apuração ética equilibra celeridade e direito de defesa?", "type": "inferential", "document": "Regimento Comitê de Conduta Ética", "expected_answer": "O processo equilibra através de prazos definidos..."}
]
```

---

## Página 10: Detalhe do Experimento

### Descrição
Acessada ao clicar "Ver Detalhes" em um experimento. Mostra configuração completa e resultados detalhados.

### Componentes:

**Header:**
- Nome do experimento com badge de status
- Botão "Voltar para Experimentos"
- Botão "Exportar CSV"

**Card de Configuração:**
Grid 2 colunas com pares label/valor:
- Coleção | EMBRAPII Sentence
- Estratégia | sentence (badge)
- Chunk Size | 512
- Chunk Overlap | 50
- Embedding Model | text-embedding-3-small
- Generator Model | gpt-4o-mini
- Retrieval Strategy | semantic
- top_k | 5
- Total Questions | 231
- Data | 2025-03-17

**Card de Métricas Médias:**
6 cards circulares (gauge/progress ring) mostrando:
- Faithfulness: 0.878
- Answer Relevancy: 0.721
- Context Precision: 0.893
- Context Recall: 0.812
- Answer Correctness: 0.679
- MRR: 0.234

**Tabela de Resultados por Pergunta:**
- Colunas: #, Pergunta, Resposta Gerada (truncada), Faithfulness, Answer Relevancy, Context Precision, Context Recall, Answer Correctness, MRR
- Cada célula de métrica com cor em escala (vermelho → amarelo → verde)
- Expansão de linha mostra:
  - Pergunta completa
  - Resposta esperada
  - Resposta gerada completa
  - Chunks recuperados

---

## Especificações Técnicas

### Stack recomendado:
- **React** com TypeScript
- **Tailwind CSS** para estilização
- **shadcn/ui** como biblioteca de componentes base
- **Recharts** ou **Nivo** para gráficos (barcharts, radar, boxplots)
- **React Router** para navegação
- **Lucide React** para ícones

### Enums e Types (TypeScript):
```typescript
type ChunkingStrategy = 'fixed_size' | 'recursive' | 'sentence' | 'semantic' | 'structure_aware';
type DocType = 'pdf' | 'xml_lattes' | 'json_lattes';
type RetrievalStrategy = 'semantic' | 'hybrid';
type ExperimentStatus = 'pending' | 'running' | 'completed' | 'failed';
type QuestionType = 'factual' | 'inferential';
```

### Mapa de cores por estratégia (consistente em toda a aplicação):
```typescript
const STRATEGY_COLORS = {
  fixed_size: '#ff6b6b',    // vermelho coral
  recursive: '#ffd93d',     // amarelo ouro
  sentence: '#00ff41',      // verde neon (destaque — é a vencedora)
  semantic: '#0984e3',      // azul elétrico
  structure_aware: '#a855f7' // roxo
};
```

### Labels em português:
```typescript
const STRATEGY_LABELS: Record<ChunkingStrategy, string> = {
  fixed_size: 'Fixed-Size',
  recursive: 'Recursive',
  sentence: 'Sentence',
  semantic: 'Semantic',
  structure_aware: 'Structure-Aware'
};

const METRIC_LABELS = {
  faithfulness: 'Faithfulness',
  answer_relevancy: 'Answer Relevancy',
  context_precision: 'Context Precision',
  context_recall: 'Context Recall',
  answer_correctness: 'Answer Correctness',
  mrr: 'MRR'
};
```

### Responsividade:
- Desktop-first (uso principal em ambiente acadêmico)
- Sidebar colapsa em telas < 1024px
- Tabelas com scroll horizontal em mobile
- Cards empilham em coluna em telas pequenas

---

## Requisitos Não-Funcionais

1. **Dados 100% mockados** — nenhuma chamada HTTP real. Todos os dados devem ser constantes/fixtures importadas de arquivos separados.
2. **Navegação funcional** — todas as rotas devem funcionar e os links da sidebar devem navegar corretamente.
3. **Interações visuais** — modais abrem/fecham, filtros filtram os dados mock, tabs alternam conteúdo, tabelas são ordenáveis.
4. **Loading states** — botões mostram spinner ao "processar" (simular com setTimeout de 1-2s).
5. **Empty states** — cada página deve ter um estado vazio elegante caso não haja dados.
6. **Toasts/Notificações** — feedback visual em ações (ex: "Coleção criada com sucesso!").
7. **Tema consistente** — o tema Matrix Acadêmico deve ser uniforme em todas as páginas.
8. **Acessibilidade básica** — contraste adequado (texto claro sobre fundo escuro), labels em formulários.

---

## Resumo Final

Este frontend é uma **interface de pesquisa e avaliação em IA** — não é um produto SaaS genérico. Deve transparecer rigor técnico, clareza de informação e sofisticação visual. O objetivo é que alguém da área de IA ou da administração pública olhe para este dashboard e imediatamente entenda:

1. Quais estratégias de chunking foram testadas
2. Como o pipeline RAG funciona
3. Quais resultados foram obtidos
4. Qual estratégia é a melhor e por quê

A interface deve parecer um **painel de controle de pesquisa em inteligência artificial** — moderna, escura, com dados claros e visualizações que contam uma história.
