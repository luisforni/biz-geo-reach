"""Message generation service: core business logic.

SOLID principles applied:
  S — one class, one purpose: generate AI messages
  D — depends on AbstractOllamaClient; concrete backend is injected

Pattern: Service Layer — sits between HTTP handlers and the Ollama adapter,
keeping route handlers thin and the generation logic independently testable.
"""

import logging

from app.clients.ollama_client import AbstractOllamaClient, OllamaClient
from app.config import settings
from app.domain.entities import ConversationMessage
from app.domain.prompt_builder import build_first_message_prompt, build_reply_prompt

logger = logging.getLogger(__name__)

class MessageService:
    """Generates personalised WhatsApp messages using the configured AI model."""

    def __init__(self, ollama: AbstractOllamaClient) -> None:
        self._ollama = ollama

    async def generate_first_message(
        self,
        commerce_name: str,
        system_prompt: str,
    ) -> str:
        """Generate a first-contact WhatsApp message for a given commerce.

        Args:
            commerce_name: Name of the target bar/restaurant.
            system_prompt: Sales persona prompt configured by the operator.

        Returns:
            Generated message text ready to be sent via WhatsApp.
        """
        messages = build_first_message_prompt(commerce_name, system_prompt)
        logger.info("Generating first message for commerce=%r", commerce_name)
        reply = await self._ollama.chat(
            messages,
            temperature=settings.temperature,
            top_p=settings.top_p,
        )
        logger.debug("First message generated (%d chars)", len(reply))
        return reply

    async def generate_reply(
        self,
        commerce_name: str,
        system_prompt: str,
        conversation: list[ConversationMessage],
    ) -> str:
        """Generate a contextual auto-sale reply for an ongoing conversation.

        Args:
            commerce_name: Name of the commerce being contacted.
            system_prompt: Sales persona prompt configured by the operator.
            conversation: Full message history up to and including the
                          latest customer message.

        Returns:
            Generated reply text ready to be sent via WhatsApp.
        """
        messages = build_reply_prompt(commerce_name, system_prompt, conversation)
        logger.info(
            "Generating reply for commerce=%r (history=%d msgs)",
            commerce_name,
            len(conversation),
        )
        reply = await self._ollama.chat(
            messages,
            temperature=settings.temperature,
            top_p=settings.top_p,
        )
        logger.debug("Reply generated (%d chars)", len(reply))
        return reply

def get_message_service() -> MessageService:
    """Factory / FastAPI dependency that wires the concrete Ollama client."""
    return MessageService(ollama=OllamaClient())
