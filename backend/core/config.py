from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_env_file = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI HCP CRM"
    API_V1_STR: str = "/api/v1"

    # Database — no SQLite fallback; startup will fail fast if missing
    DATABASE_URL: str

    # LLM
    GROQ_API_KEY: Optional[str] = None
    PRIMARY_MODEL: str = "gemma2-9b-it"
    SECONDARY_MODEL: str = "llama-3.3-70b-versatile"

    # Environment
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


def _validate_settings(s: Settings) -> Settings:
    if "sqlite" in s.DATABASE_URL.lower():
        raise RuntimeError(
            "SQLite is not allowed. Set a PostgreSQL DATABASE_URL in backend/.env"
        )
    if not s.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing from backend/.env")
    return s


settings = _validate_settings(Settings())
