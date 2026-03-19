"""API key authentication dependency.

OWASP A07 — Identification and Authentication Failures:
  - hmac.compare_digest prevents timing-based key enumeration.
  - Returns generic 401 without revealing key details.
"""

import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

logger = logging.getLogger(__name__)

_api_key_scheme = APIKeyHeader(name=settings.api_key_header, auto_error=False)

def require_api_key(
    api_key: str | None = Security(_api_key_scheme),
) -> None:
    """FastAPI dependency: validates the API key in the request header."""
    provided = api_key or ""
    if not hmac.compare_digest(provided.encode(), settings.api_key.encode()):
        logger.warning("Unauthorized request — invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
