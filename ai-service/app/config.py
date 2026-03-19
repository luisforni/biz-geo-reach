"""Application configuration loaded from environment variables."""

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Commerce Finder AI Service"
    debug: bool = False
    port: int = 8002

    api_key: str = secrets.token_hex(32)
    api_key_header: str = "X-API-Key"
    allowed_origins: list[str] = [
        "http://localhost:8001",
        "http://localhost:5173",
    ]

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 60.0

    temperature: float = 0.7
    top_p: float = 0.9

    rate_limit_per_minute: int = 30

settings = Settings()
