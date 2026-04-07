from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sme_news"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    DEBUG: bool = False
    APP_VERSION: str = "0.1.0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
