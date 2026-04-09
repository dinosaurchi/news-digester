from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sme_news"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]
    DEBUG: bool = False
    APP_VERSION: str = "0.1.0"

    # OpenCode Agent Adapter (backend-facing)
    OPENCODE_BASE_URL: str = "http://opencode-agent-adapter:8080"
    OPENCODE_TIMEOUT_SECONDS: int = 60
    OPENCODE_ENABLED: bool = False
    OPENCODE_DEFAULT_MODEL: str = "opencode/gpt-5-nano"
    OPENCODE_DEFAULT_AGENT: str = "general"
    OPENCODE_WORKSPACE_DIR: str = "/workspace"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
