from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENAI_API_KEY: str
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    COHERE_API_KEY: str
    COHERE_RERANK_MODEL: str = "rerank-multilingual-v3.0"

    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_TABLE: str = "documents"
    SUPABASE_QUERY_NAME: str = "match_documents"

    DATABASE_URL: str

    HISTORY_LIMIT: int = 10
    RETRIEVER_K: int = 12
    RERANK_TOP_N: int = 4
    RERANK_MIN_SCORE: float = 0.2
    MATCH_THRESHOLD: float = 0.0

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    MAX_INPUT_LENGTH: int = 1000

    ADMIN_API_KEY: str

    ALLOWED_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
