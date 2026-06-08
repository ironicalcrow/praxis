from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # LLM Settings (OpenAI-compatible) — used for CV parsing, job queries
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str

    # LLM fallback — tried when primary returns 429 / 402 / 503
    LLM_FALLBACK_API_KEY: Optional[str] = None
    LLM_FALLBACK_BASE_URL: Optional[str] = None
    LLM_FALLBACK_MODEL: Optional[str] = None

    # Chatbot Settings — used for chat, roadmap generation
    CHATBOT_API_KEY: str
    CHATBOT_BASE_URL: str
    CHATBOT_LLM_MODEL: str

    # Chatbot fallback
    CHATBOT_FALLBACK_API_KEY: Optional[str] = None
    CHATBOT_FALLBACK_BASE_URL: Optional[str] = None
    CHATBOT_FALLBACK_MODEL: Optional[str] = None

    # Embedding Settings
    EMBEDDING_API_KEY: str
    EMBEDDING_BASE_URL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSIONS: int = 1536

    # Embedding fallback
    EMBEDDING_FALLBACK_API_KEY: Optional[str] = None
    EMBEDDING_FALLBACK_BASE_URL: Optional[str] = None
    EMBEDDING_FALLBACK_MODEL: Optional[str] = None

    JSEARCH_API_KEYS: str
    JSEARCH_API_HOST: str
    JSEARCH_URL: str
    JSEARCH_DETAIL_URL: str

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "cvs"

    DATABASE_URL: str
    REDIS_URL: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore"
    )


settings = Settings()
