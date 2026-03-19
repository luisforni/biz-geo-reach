import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.whatsapp_client import WhatsAppClient, WhatsAppGatewayError
from app.database.engine import get_db_session
from app.database.repository import SQLiteContactRepository
from app.domain.campaign.entities import (
    ContactConversationResponse,
    ContactPatchRequest,
    ContactResponse,
    ConversationMessage,
    ManualMessageRequest,
)
from app.domain.campaign.service import CampaignService, get_campaign_service
from app.middleware.auth import require_api_key

router = APIRouter(prefix="/campaigns", tags=["contacts"])

logger = logging.getLogger(__name__)


def _svc(session: AsyncSession = Depends(get_db_session)) -> CampaignService:
    return get_campaign_service(session)


@router.get(
    "/{campaign_id}/contacts",
    response_model=list[ContactResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_contacts(
    campaign_id: int,
    svc: CampaignService = Depends(_svc),
) -> list[ContactResponse]:
    campaign = await svc.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return await svc.list_contacts(campaign_id)


@router.get(
    "/{campaign_id}/contacts/{contact_id}/conversation",
    response_model=ContactConversationResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_conversation(
    campaign_id: int,
    contact_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ContactConversationResponse:
    repo = SQLiteContactRepository(session)
    contact = await repo.get_by_id(contact_id)

    if contact is None or contact.campaign_id != campaign_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    raw_messages: list[dict] = []
    if contact.conversation_json:
        try:
            raw_messages = json.loads(contact.conversation_json)
        except (json.JSONDecodeError, TypeError):
            raw_messages = []

    messages = [ConversationMessage(**m) for m in raw_messages]

    return ContactConversationResponse(
        contact_id=contact.id,
        commerce_name=contact.commerce_name,
        state=contact.state,
        messages=messages,
    )


@router.patch(
    "/{campaign_id}/contacts/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_api_key)],
)
async def update_contact(
    campaign_id: int,
    contact_id: int,
    payload: ContactPatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ContactResponse:
    repo = SQLiteContactRepository(session)
    contact = await repo.get_by_id(contact_id)

    if contact is None or contact.campaign_id != campaign_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if payload.manual_mode is not None:
        await repo.set_manual_mode(contact_id, payload.manual_mode)
        await session.commit()
        contact = await repo.get_by_id(contact_id)

    return ContactResponse.model_validate(contact)


@router.post(
    "/{campaign_id}/contacts/{contact_id}/send",
    dependencies=[Depends(require_api_key)],
)
async def send_manual_message(
    campaign_id: int,
    contact_id: int,
    payload: ManualMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    repo = SQLiteContactRepository(session)
    contact = await repo.get_by_id(contact_id)

    if contact is None or contact.campaign_id != campaign_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    phone = contact.phone_normalized or contact.phone_raw
    if not phone:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Contact has no phone number")

    wa = WhatsAppClient()
    try:
        await wa.send_message(phone, payload.message)
    except WhatsAppGatewayError as exc:
        logger.error("Manual send failed for contact %d: %s", contact_id, exc)
        raise HTTPException(status_code=502, detail=f"WhatsApp gateway error: {exc}")

    raw: list[dict] = []
    if contact.conversation_json:
        try:
            raw = json.loads(contact.conversation_json)
        except (json.JSONDecodeError, TypeError):
            raw = []

    raw.append({
        "role": "operator",
        "content": payload.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await repo.update_conversation(contact_id, json.dumps(raw))
    await repo.set_manual_mode(contact_id, True)
    await session.commit()

    logger.info("Manual message sent to contact %d — manual_mode=True", contact_id)
    return {"status": "sent", "manual_mode": True}
