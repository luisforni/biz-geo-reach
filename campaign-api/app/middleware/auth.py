import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

logger = logging.getLogger(__name__)

_api_key_scheme = APIKeyHeader(name=settings.api_key_header, auto_error=False)

_UNCONFIGURED_KEY = "change-me"

def require_api_key(
    api_key: str | None = Security(_api_key_scheme),
) -> None:
    if settings.api_key == _UNCONFIGURED_KEY:
        return
    provided = api_key or ""
    if not hmac.compare_digest(provided.encode(), settings.api_key.encode()):
        logger.warning("Unauthorized request — invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
