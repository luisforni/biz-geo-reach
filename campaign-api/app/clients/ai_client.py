"""HTTP adapter for the ai-service.

Pattern: Adapter — abstracts the HTTP transport so the worker and webhook
handler only deal with domain concepts (commerce name, conversation history).
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Raised when the ai-service returns an error or is unreachable."""

class AIClient:
    """Async HTTP client for the ai-service."""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url or settings.ai_service_url
        self._api_key = api_key or settings.ai_service_api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def generate_first_message(
        self,
        commerce_name: str,
        system_prompt: str,
    ) -> str:
        """Generate a personalized first-contact WhatsApp message via the AI service."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/generate/first-message",
                    json={
                        "commerce_name": commerce_name,
                        "system_prompt": system_prompt,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()["message"]
            except httpx.HTTPStatusError as exc:
                logger.error("ai-service first-message error: %s", exc)
                raise AIServiceError(str(exc)) from exc
            except httpx.RequestError as exc:
                logger.error("ai-service unreachable: %s", exc)
                raise AIServiceError(str(exc)) from exc

    async def generate_reply(
        self,
        commerce_name: str,
        system_prompt: str,
        conversation: list[dict[str, Any]],
    ) -> str:
        """Generate a contextual auto-sale reply for an ongoing conversation."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/generate/reply",
                    json={
                        "commerce_name": commerce_name,
                        "system_prompt": system_prompt,
                        "conversation": conversation,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()["message"]
            except httpx.HTTPStatusError as exc:
                logger.error("ai-service reply error: %s", exc)
                raise AIServiceError(str(exc)) from exc
            except httpx.RequestError as exc:
                logger.error("ai-service unreachable: %s", exc)
                raise AIServiceError(str(exc)) from exc
