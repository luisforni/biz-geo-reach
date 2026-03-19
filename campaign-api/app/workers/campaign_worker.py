"""Campaign worker: drives contacts through their lifecycle.

Runs as a background asyncio task. Processes one PENDING contact per
active campaign per poll cycle to avoid flooding WhatsApp.

Flow per contact:
  PENDING
    → normalize phone (invalid → ERROR)
    → VALIDATING_WHATSAPP (gateway check)
        → NO_WHATSAPP (skip)
        → SENDING_FIRST_MESSAGE
            → generate AI message
            → send via gateway
            → WAITING_RESPONSE  (webhook takes over from here)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.clients.ai_client import AIClient, AIServiceError
from app.clients.whatsapp_client import WhatsAppClient, WhatsAppGatewayError
from app.config import settings
from app.database.engine import AsyncSessionLocal
from app.database.repository import SQLiteCampaignRepository, SQLiteContactRepository
from app.domain.campaign.state_machine import ContactState
from app.domain.phone.normalizer import normalize_phone

logger = logging.getLogger(__name__)

class CampaignWorker:
    """Background worker that polls for pending contacts and processes them."""

    def __init__(self) -> None:
        self._wa = WhatsAppClient()
        self._ai = AIClient()
        self._running = False

    async def start(self) -> None:
        """Run the poll loop until stop() is called."""
        self._running = True
        logger.info(
            "Campaign worker started (interval=%ds)",
            settings.worker_poll_interval_seconds,
        )
        while self._running:
            try:
                await self._poll()
            except Exception as exc:
                logger.exception("Unhandled worker error: %s", exc)
            await asyncio.sleep(settings.worker_poll_interval_seconds)

    def stop(self) -> None:
        """Signal the poll loop to exit after the current iteration."""
        self._running = False

    async def _poll(self) -> None:
        """Process one PENDING contact per active campaign."""
        async with AsyncSessionLocal() as session:
            campaign_repo = SQLiteCampaignRepository(session)
            contact_repo = SQLiteContactRepository(session)

            campaigns = await campaign_repo.list_all()
            for campaign in campaigns:
                if campaign.status != "active":
                    continue

                contact = await contact_repo.get_next_pending(campaign.id)
                if contact is None:
                    continue

                logger.info(
                    "Processing contact id=%d commerce=%r campaign=%d",
                    contact.id,
                    contact.commerce_name,
                    campaign.id,
                )
                await self._process_contact(
                    session, contact_repo, contact, campaign
                )

    async def _process_contact(self, session, contact_repo, contact, campaign) -> None:
        """Run the full PENDING → WAITING_RESPONSE pipeline for one contact."""

        phone = normalize_phone(contact.phone_raw, settings.default_region)
        if phone is None:
            await contact_repo.transition_state(
                contact.id,
                ContactState.ERROR,
                notes="Could not normalize phone number",
            )
            await session.commit()
            logger.warning(
                "Invalid phone for contact %d: %r", contact.id, contact.phone_raw
            )
            return

        await contact_repo.transition_state(
            contact.id,
            ContactState.VALIDATING_WHATSAPP,
            phone_normalized=phone,
        )
        await session.commit()

        try:
            result = await self._wa.validate_phone(phone)
        except WhatsAppGatewayError as exc:
            await contact_repo.transition_state(
                contact.id,
                ContactState.PENDING,
                notes=f"Gateway unavailable, will retry: {exc}",
            )
            await session.commit()
            logger.warning("WA gateway unavailable for contact %d — reset to PENDING", contact.id)
            return

        if not result.has_whatsapp:
            await contact_repo.transition_state(
                contact.id,
                ContactState.NO_WHATSAPP,
                notes="Number has no WhatsApp account",
            )
            await session.commit()
            logger.info("No WhatsApp for contact %d (%s)", contact.id, phone)
            return

        await contact_repo.transition_state(
            contact.id, ContactState.SENDING_FIRST_MESSAGE
        )
        await session.commit()

        try:
            message = await self._ai.generate_first_message(
                commerce_name=contact.commerce_name,
                system_prompt=campaign.system_prompt,
            )
        except AIServiceError as exc:
            await contact_repo.transition_state(
                contact.id,
                ContactState.ERROR,
                notes=f"AI generation error: {exc}",
            )
            await session.commit()
            return

        try:
            await self._wa.send_message(phone, message)
        except WhatsAppGatewayError as exc:
            await contact_repo.transition_state(
                contact.id,
                ContactState.ERROR,
                notes=f"WhatsApp send error: {exc}",
            )
            await session.commit()
            return

        conversation = [
            {
                "role": "assistant",
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
        await contact_repo.update_conversation(contact.id, json.dumps(conversation))
        await contact_repo.mark_first_message_sent(contact.id)
        await session.commit()

        logger.info(
            "First message sent to contact %d (%s) — now WAITING_RESPONSE",
            contact.id,
            phone,
        )

_worker: CampaignWorker | None = None

def get_worker() -> CampaignWorker:
    """Return the application-wide CampaignWorker instance."""
    global _worker
    if _worker is None:
        _worker = CampaignWorker()
    return _worker
