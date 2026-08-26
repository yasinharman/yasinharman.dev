from functools import lru_cache
from typing import Literal

from pydantic import model_validator
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

    # Çalışma modu — DB kalıcılığını (chat_messages + chat_logs) belirleyen tek anahtar.
    #   prod  : normal davranış; DATABASE_URL zorunlu, her mesaj DB'ye yazılır.
    #   local : geliştirme; DB'ye hiçbir şey yazılmaz, prod verisi kirlenmez.
    # Varsayılan bilinçli olarak "prod": Coolify'da MODE tanımlanmasa bile prod
    # davranışı geçerli olur ve eksik DATABASE_URL startup'ta çöker (fail-fast).
    MODE: Literal["local", "prod"] = "prod"
    DATABASE_URL: str | None = None

    HISTORY_LIMIT: int = 10
    RETRIEVER_K: int = 12
    RERANK_TOP_N: int = 8
    RERANK_MIN_SCORE: float = 0.3
    MATCH_THRESHOLD: float = 0.0

    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 150

    MAX_INPUT_LENGTH: int = 1000

    # /chat auth'suz ve halka acik. MAX_INPUT_LENGTH mesaj boyutunu sinirliyor ama
    # istek SAYISINI degil; her istek 2-5 OpenAI + 2-5 Cohere cagrisi demek.
    RATE_LIMIT_PER_MIN: int = 20    # IP basina
    RATE_LIMIT_PER_DAY: int = 100   # session_id basina

    ADMIN_API_KEY: str

    ALLOWED_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    @model_validator(mode="after")
    def _require_database_url_in_prod(self) -> "Settings":
        if self.MODE == "prod" and not self.DATABASE_URL:
            raise ValueError(
                "MODE=prod iken DATABASE_URL zorunludur. "
                "Lokal geliştirme için MODE=local verin."
            )
        return self

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
