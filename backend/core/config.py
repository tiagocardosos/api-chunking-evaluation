from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_url: str = "postgresql://rag:rag123@localhost:5432/rag_eval"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    generator_model: str = "gpt-4o-mini"
    top_k: int = 5
    cors_allowed_origins: str = "http://localhost:8080,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
