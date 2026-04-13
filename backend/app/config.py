from pydantic import model_validator
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

    # OpenCode Agent Adapter (required — no disabled mode)
    OPENCODE_BASE_URL: str = "http://opencode-agent-adapter:8080"
    OPENCODE_TIMEOUT_SECONDS: int = 60
    OPENCODE_DEFAULT_MODEL: str = "opencode/gpt-5-nano"
    OPENCODE_DEFAULT_AGENT: str = "general"
    OPENCODE_WORKSPACE_DIR: str = "/workspace"

    # Dev/admin bootstrap. Production deployments should override these values
    # and rotate the password after first launch.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_DISPLAY_NAME: str = "Admin"
    ADMIN_ROLE: str = "admin"

    # Session storage
    SESSION_TTL_SECONDS: int = 86_400  # 24 hours

    # Article body enrichment (optional pipeline step)
    ARTICLE_ENRICHMENT_ENABLED: bool = False
    ARTICLE_ENRICHMENT_TIMEOUT_SECONDS: int = 5
    ARTICLE_BODY_MAX_LENGTH: int = 10000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_opencode_config(self) -> "Settings":
        """Fail if required OpenCode configuration is missing or invalid."""
        missing: list[str] = []
        for field in (
            "OPENCODE_BASE_URL",
            "OPENCODE_DEFAULT_MODEL",
            "OPENCODE_DEFAULT_AGENT",
            "OPENCODE_WORKSPACE_DIR",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                missing.append(field)
        if self.OPENCODE_TIMEOUT_SECONDS <= 0:
            missing.append("OPENCODE_TIMEOUT_SECONDS (must be > 0)")
        if missing:
            raise ValueError(
                "Required OpenCode configuration is missing or invalid: "
                + ", ".join(missing)
            )
        return self


settings = Settings()
