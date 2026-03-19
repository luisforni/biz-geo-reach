"""Timeout scheduler: moves stale WAITING_RESPONSE contacts to TIMED_OUT.

Runs as a background asyncio task, checking every hour.
A contact is considered timed out when its first_message_sent_at is older
than RESPONSE_TIMEOUT_HOURS without receiving a reply webhook.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database.engine import AsyncSessionLocal
from app.database.repository import SQLiteContactRepository
from app.domain.campaign.state_machine import ContactState

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 3_600

class TimeoutScheduler:
    """Periodically marks contacts as TIMED_OUT when they exceed the wait window."""

    def __init__(self) -> None:
        self._running = False

    async def start(self) -> None:
        """Run the check loop until stop() is called."""
        self._running = True
        logger.info(
            "Timeout scheduler started (check every %ds, timeout=%dh)",
            _CHECK_INTERVAL_SECONDS,
            settings.response_timeout_hours,
        )
        while self._running:
            try:
                await self._check_timeouts()
            except Exception as exc:
                logger.exception("Scheduler error: %s", exc)
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Signal the loop to exit after the current sleep."""
        self._running = False

    async def _check_timeouts(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=settings.response_timeout_hours
        )
        async with AsyncSessionLocal() as session:
            repo = SQLiteContactRepository(session)
            contacts = await repo.get_waiting_since_before(cutoff)

            if not contacts:
                return

            for contact in contacts:
                await repo.transition_state(
                    contact.id,
                    ContactState.TIMED_OUT,
                    notes=f"No reply after {settings.response_timeout_hours}h",
                )
                logger.info("Contact %d timed out", contact.id)

            await session.commit()
            logger.info("Marked %d contact(s) as timed out", len(contacts))

_scheduler: TimeoutScheduler | None = None

def get_scheduler() -> TimeoutScheduler:
    """Return the application-wide TimeoutScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TimeoutScheduler()
    return _scheduler
