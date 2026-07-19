"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. All values can be overridden via environment variables."""

    # WARNING: this default is for local development only.
    # In production you MUST set a strong, random SECRET_KEY via environment variable.
    SECRET_KEY: str = "dev-only-insecure-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    DATABASE_URL: str = "sqlite:///./devboard.db"

    # Comma-separated list of allowed CORS origins (frontend dev server by default)
    CORS_ORIGINS: str = "http://localhost:5173"

    # AI task parsing (OpenAI-compatible chat completions API). When AI_API_KEY
    # is empty, /tasks/ai-parse falls back to the built-in rule-based parser.
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
