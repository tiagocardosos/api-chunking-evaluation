# Agents - Configuracao do Projeto

Agentes especializados para o projeto **rag-chunking-evaluation** (mestrado).

## Agentes Disponiveis

| Agente | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| Backend Developer | `backend-developer.md` | FastAPI, Qdrant, PostgreSQL, chunking, RAG |
| Programming | `programming.md` | Regras globais de codigo (aplica automaticamente) |
| Code Reviewer | `code-reviewer.md` | Revisao de qualidade, seguranca, padroes |
| Test Runner | `test-runner.md` | Execucao de testes pytest e cobertura |
| Git Workflow | `git-workflow.md` | Commits convencionais, branches |

## Categorias

### Desenvolvimento
- **backend-developer** - APIs, banco de dados, chunking, RAG
- **programming** - Padroes e regras (sempre ativo)

### Qualidade
- **code-reviewer** - Revisao de codigo
- **test-runner** - Testes e cobertura

### Workflow
- **git-workflow** - Operacoes git e commits

## Stack do Projeto

- **Linguagem:** Python 3.12+
- **Framework:** FastAPI
- **Pacotes:** uv
- **Lint/Format:** Ruff
- **Testes:** pytest
- **Infra:** Docker Compose (local)
- **Banco:** PostgreSQL 16 + Qdrant
