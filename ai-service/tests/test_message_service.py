"""Unit tests for MessageService using a mock Ollama client.

The mock lets us verify service behaviour without needing a running Ollama
instance, which is correct test isolation for a unit test.
"""

import pytest

from app.clients.ollama_client import AbstractOllamaClient, OllamaError
from app.domain.entities import ConversationMessage
from app.services.message_service import MessageService

class _MockOllamaClient(AbstractOllamaClient):
    """Stub that returns a fixed reply without making HTTP calls."""

    def __init__(self, response: str = "Mensaje de prueba.") -> None:
        self._response = response
        self.last_messages: list[dict] = []
        self.call_count = 0

    async def chat(self, messages, temperature=0.7, top_p=0.9) -> str:
        self.last_messages = messages
        self.call_count += 1
        return self._response

class _FailingOllamaClient(AbstractOllamaClient):
    """Stub that always raises OllamaError."""

    async def chat(self, messages, temperature=0.7, top_p=0.9) -> str:
        raise OllamaError("Ollama is down")

@pytest.mark.asyncio
async def test_generate_first_message_returns_model_reply():
    mock = _MockOllamaClient("¡Hola! Te cuento sobre nuestros servicios.")
    svc = MessageService(mock)

    result = await svc.generate_first_message("Bar El Sol", "Sos un vendedor.")

    assert result == "¡Hola! Te cuento sobre nuestros servicios."

@pytest.mark.asyncio
async def test_generate_first_message_calls_ollama_once():
    mock = _MockOllamaClient()
    svc = MessageService(mock)

    await svc.generate_first_message("Café Luna", "Prompt.")

    assert mock.call_count == 1

@pytest.mark.asyncio
async def test_generate_first_message_includes_commerce_name_in_prompt():
    mock = _MockOllamaClient()
    svc = MessageService(mock)

    await svc.generate_first_message("Parrilla Don Roberto", "Prompt.")

    system_content = mock.last_messages[0]["content"]
    assert "Parrilla Don Roberto" in system_content

@pytest.mark.asyncio
async def test_generate_first_message_propagates_ollama_error():
    svc = MessageService(_FailingOllamaClient())

    with pytest.raises(OllamaError):
        await svc.generate_first_message("Bar", "Prompt.")

@pytest.mark.asyncio
async def test_generate_reply_returns_model_reply():
    mock = _MockOllamaClient("Claro, te paso más info.")
    svc = MessageService(mock)
    conversation = [ConversationMessage(role="user", content="¿Cuánto cuesta?")]

    result = await svc.generate_reply("Bar", "Prompt.", conversation)

    assert result == "Claro, te paso más info."

@pytest.mark.asyncio
async def test_generate_reply_includes_full_history():
    mock = _MockOllamaClient()
    svc = MessageService(mock)
    conversation = [
        ConversationMessage(role="assistant", content="Primer mensaje"),
        ConversationMessage(role="user", content="Me interesa"),
    ]

    await svc.generate_reply("Bar", "Prompt.", conversation)

    assert len(mock.last_messages) == 3

@pytest.mark.asyncio
async def test_generate_reply_propagates_ollama_error():
    svc = MessageService(_FailingOllamaClient())
    conversation = [ConversationMessage(role="user", content="Hola")]

    with pytest.raises(OllamaError):
        await svc.generate_reply("Bar", "Prompt.", conversation)
