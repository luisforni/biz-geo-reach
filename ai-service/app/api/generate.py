"""AI generation endpoints.

POST /generate/first-message  — personalised first-contact message
POST /generate/reply          — contextual auto-sale conversation reply
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.ollama_client import OllamaError
from app.domain.entities import FirstMessageRequest, MessageResponse, ReplyRequest
from app.middleware.auth import require_api_key
from app.services.message_service import MessageService, get_message_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])

def _svc() -> MessageService:
    return get_message_service()

@router.post(
    "/first-message",
    response_model=MessageResponse,
    dependencies=[Depends(require_api_key)],
)
async def first_message(
    payload: FirstMessageRequest,
    svc: MessageService = Depends(_svc),
) -> MessageResponse:
    """Generate a personalised first-contact WhatsApp message.

    The message is crafted using the operator's system prompt and the
    target commerce's name, then returned for the campaign-service to send.
    """
    try:
        message = await svc.generate_first_message(
            commerce_name=payload.commerce_name,
            system_prompt=payload.system_prompt,
        )
    except OllamaError as exc:
        logger.error("Ollama error on first-message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI model unavailable: {exc}",
        )

    return MessageResponse(message=message)

@router.post(
    "/reply",
    response_model=MessageResponse,
    dependencies=[Depends(require_api_key)],
)
async def reply(
    payload: ReplyRequest,
    svc: MessageService = Depends(_svc),
) -> MessageResponse:
    """Generate a contextual auto-sale reply for an ongoing conversation.

    Receives the full conversation history so the model can produce a
    coherent, context-aware response. Only called when auto_sale=ON.
    """
    try:
        message = await svc.generate_reply(
            commerce_name=payload.commerce_name,
            system_prompt=payload.system_prompt,
            conversation=payload.conversation,
        )
    except OllamaError as exc:
        logger.error("Ollama error on reply: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI model unavailable: {exc}",
        )

    return MessageResponse(message=message)
