"""Application configuration loaded from environment variables.

Pydantic Settings validates types and provides defaults.
Secrets are never logged (OWASP A09).
"""

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Commerce Finder Campaign Service"
    debug: bool = False
    port: int = 8001

    api_key: str = secrets.token_hex(32)
    api_key_header: str = "X-API-Key"
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8090",
    ]

    database_url: str = "sqlite+aiosqlite:///./data/campaigns.db"

    whatsapp_gateway_url: str = "http://localhost:3001"
    whatsapp_gateway_api_key: str = ""
    ai_service_url: str = "http://localhost:8002"
    ai_service_api_key: str = ""

    worker_poll_interval_seconds: int = 10
    response_timeout_hours: int = 24

    default_region: str = "AR"

    rate_limit_per_minute: int = 60

settings = Settings()
