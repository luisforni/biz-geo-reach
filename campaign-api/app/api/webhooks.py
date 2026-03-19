"""Webhook endpoint: receives incoming WhatsApp messages from the gateway.

When a customer replies, this handler:
  1. Finds the active contact by phone number.
  2. Appends the message to the conversation history.
  3. If auto_sale=OFF → marks contact as COMPLETED.
  4. If auto_sale=ON  → asks the AI for a reply and sends it back.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_client import AIClient, AIServiceError
from app.clients.whatsapp_client import WhatsAppClient, WhatsAppGatewayError
from app.database.engine import get_db_session
from app.database.repository import SQLiteCampaignRepository, SQLiteContactRepository
from app.domain.campaign.entities import IncomingWhatsAppMessage
from app.domain.campaign.state_machine import ContactState
from app.middleware.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_SCHEDULED_CALL_KEYWORDS = (
    "llamada",
    "te llamo",
    "llámame",
    "agendamos",
    "coordinar",
    "horario",
    "fecha",
    "reunión",
)

@router.post(
    "/whatsapp",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_api_key)],
)
async def receive_whatsapp_message(
    payload: IncomingWhatsAppMessage,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Handle an incoming WhatsApp message pushed by the gateway."""
    contact_repo = SQLiteContactRepository(session)
    campaign_repo = SQLiteCampaignRepository(session)

    contact, campaign = None, None
    for c in await campaign_repo.list_all():
        if c.status != "active":
            continue
        found = await contact_repo.find_by_phone(payload.phone, c.id)
        if found and found.state in (
            ContactState.WAITING_RESPONSE,
            ContactState.IN_CONVERSATION,
        ):
            contact, campaign = found, c
            break

    if contact is None:
        logger.info("Ignored webhook — no active contact for phone %s", payload.phone)
        return {"status": "ignored"}

    conversation = _parse_conversation(contact.conversation_json)
    conversation.append(
        {
            "role": "user",
            "content": payload.message,
            "timestamp": payload.timestamp.isoformat(),
        }
    )

    if contact.manual_mode:
        await contact_repo.update_conversation(contact.id, json.dumps(conversation))
        await session.commit()
        logger.info("Contact %d in manual mode — auto-reply skipped", contact.id)
        return {"status": "manual_mode"}

    if not campaign.auto_sales_enabled:
        await contact_repo.transition_state(contact.id, ContactState.COMPLETED)
        await contact_repo.update_conversation(contact.id, json.dumps(conversation))
        await session.commit()
        logger.info("Contact %d completed (auto_sales=off)", contact.id)
        return {"status": "completed"}

    ai = AIClient()
    wa = WhatsAppClient()

    try:
        reply_text = await ai.generate_reply(
            commerce_name=contact.commerce_name,
            system_prompt=campaign.system_prompt,
            conversation=conversation,
        )
    except AIServiceError as exc:
        logger.error("AI reply failed for contact %d: %s", contact.id, exc)
        await contact_repo.transition_state(
            contact.id, ContactState.ERROR, notes=f"AI error: {exc}"
        )
        raise HTTPException(status_code=502, detail="AI service unavailable")

    try:
        await wa.send_message(contact.phone_normalized, reply_text)
    except WhatsAppGatewayError as exc:
        logger.error("Send reply failed for contact %d: %s", contact.id, exc)
        await contact_repo.transition_state(
            contact.id, ContactState.ERROR, notes=f"WA send error: {exc}"
        )
        raise HTTPException(status_code=502, detail="WhatsApp gateway unavailable")

    conversation.append(
        {
            "role": "assistant",
            "content": reply_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    await contact_repo.update_conversation(contact.id, json.dumps(conversation))

    new_state = _detect_terminal_state(reply_text)
    await contact_repo.transition_state(contact.id, new_state)
    await session.commit()

    logger.info("Contact %d replied → state=%s", contact.id, new_state)
    return {"status": "replied", "new_state": new_state}

def _parse_conversation(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

def _detect_terminal_state(reply_text: str) -> ContactState:
    """Heuristic: if the AI's reply implies scheduling a call → SCHEDULED_CALL."""
    lower = reply_text.lower()
    if any(kw in lower for kw in _SCHEDULED_CALL_KEYWORDS):
        return ContactState.SCHEDULED_CALL
    return ContactState.IN_CONVERSATION
