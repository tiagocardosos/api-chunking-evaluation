FROM python:3.12-slim

# Copia o binário do uv da imagem oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copia apenas os arquivos de dependência primeiro (cache layer)
COPY pyproject.toml ./

# Instala dependências de produção no Python do sistema (sem venv dentro do container)
RUN uv pip install --system -r pyproject.toml

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
