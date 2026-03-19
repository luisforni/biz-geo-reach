"""HTTP adapter for the Ollama REST API.

Pattern: Adapter — isolates all Ollama-specific HTTP details so the service
layer only talks to the abstract interface.

SOLID — Dependency Inversion: MessageService depends on AbstractOllamaClient,
not on the concrete HTTP implementation.

Ollama /api/chat reference:
  POST http://localhost:11434/api/chat
  Body: { model, messages, stream: false, options: { temperature, top_p } }
  Response: { message: { role, content }, done: true }
"""

import logging
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Raised when Ollama returns an error or is unreachable."""

class AbstractOllamaClient(ABC):
    """Interface for the Ollama chat completion backend."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str: ...

class OllamaClient(AbstractOllamaClient):
    """Concrete async HTTP client for the local Ollama service."""

    def __init__(
        self,
        base_url: str = "",
        model: str = "",
        timeout: float = 0.0,
    ) -> None:
        self._base_url = (base_url or settings.ollama_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._timeout = timeout or settings.ollama_timeout_seconds

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Send a chat completion request to Ollama.

        Args:
            messages: List of {role, content} dicts (system / user / assistant).
            temperature: Sampling temperature (higher = more creative).
            top_p: Nucleus sampling threshold.

        Returns:
            The model's reply as a plain string.

        Raises:
            OllamaError: On HTTP error or connection failure.
        """
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content: str = data["message"]["content"]
                logger.debug(
                    "Ollama response: model=%s tokens=%s",
                    self._model,
                    data.get("eval_count", "?"),
                )
                return content.strip()
            except httpx.HTTPStatusError as exc:
                logger.error("Ollama HTTP error: %s", exc)
                raise OllamaError(f"Ollama returned {exc.response.status_code}") from exc
            except httpx.RequestError as exc:
                logger.error("Ollama unreachable: %s", exc)
                raise OllamaError(f"Ollama unreachable: {exc}") from exc
            except (KeyError, ValueError) as exc:
                logger.error("Unexpected Ollama response format: %s", exc)
                raise OllamaError("Unexpected response format from Ollama") from exc
