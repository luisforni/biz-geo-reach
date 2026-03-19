"""Repository pattern: abstract interfaces + SQLite (SQLAlchemy) implementations.

SOLID principles applied:
  S — each class manages one aggregate root (Campaign or Contact)
  O — new storage backends extend the abstract class without changing callers
  D — service layer depends on abstract interfaces, not concrete classes
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Campaign, Contact
from app.domain.campaign.entities import CampaignCreate, ContactInput
from app.domain.campaign.state_machine import ContactState

class AbstractCampaignRepository(ABC):
    """Read/write interface for Campaign aggregates."""

    @abstractmethod
    async def create(self, payload: CampaignCreate) -> Campaign: ...

    @abstractmethod
    async def get_by_id(self, campaign_id: int) -> Optional[Campaign]: ...

    @abstractmethod
    async def list_all(self) -> list[Campaign]: ...

    @abstractmethod
    async def update_status(self, campaign_id: int, status: str) -> None: ...

class AbstractContactRepository(ABC):
    """Read/write interface for Contact aggregates."""

    @abstractmethod
    async def bulk_create(
        self, campaign_id: int, contacts: list[ContactInput]
    ) -> list[Contact]: ...

    @abstractmethod
    async def get_by_id(self, contact_id: int) -> Optional[Contact]: ...

    @abstractmethod
    async def list_by_campaign(self, campaign_id: int) -> list[Contact]: ...

    @abstractmethod
    async def get_next_pending(self, campaign_id: int) -> Optional[Contact]: ...

    @abstractmethod
    async def get_waiting_since_before(
        self, cutoff: datetime
    ) -> list[Contact]: ...

    @abstractmethod
    async def find_by_phone(
        self, phone_normalized: str, campaign_id: int
    ) -> Optional[Contact]: ...

    @abstractmethod
    async def transition_state(
        self,
        contact_id: int,
        new_state: ContactState,
        *,
        phone_normalized: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None: ...

    @abstractmethod
    async def mark_first_message_sent(self, contact_id: int) -> None: ...

    @abstractmethod
    async def update_conversation(
        self, contact_id: int, conversation_json: str
    ) -> None: ...

    @abstractmethod
    async def set_manual_mode(self, contact_id: int, manual_mode: bool) -> None: ...

class SQLiteCampaignRepository(AbstractCampaignRepository):
    """Concrete implementation backed by SQLite via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(
            name=payload.name,
            description=payload.description,
            system_prompt=payload.system_prompt,
            auto_sales_enabled=payload.auto_sales_enabled,
            wait_hours_no_reply=payload.wait_hours_no_reply,
            max_auto_messages=payload.max_auto_messages,
        )
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        return campaign

    async def get_by_id(self, campaign_id: int) -> Optional[Campaign]:
        result = await self._session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Campaign]:
        result = await self._session.execute(
            select(Campaign).order_by(Campaign.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, campaign_id: int, status: str) -> None:
        await self._session.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(status=status, updated_at=func.now())
        )

class SQLiteContactRepository(AbstractContactRepository):
    """Concrete implementation backed by SQLite via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self, campaign_id: int, contacts: list[ContactInput]
    ) -> list[Contact]:
        rows = [
            Contact(
                campaign_id=campaign_id,
                commerce_name=c.commerce_name,
                phone_raw=c.phone_raw,
                state=ContactState.PENDING,
            )
            for c in contacts
        ]
        self._session.add_all(rows)
        await self._session.flush()
        for row in rows:
            await self._session.refresh(row)
        return rows

    async def get_by_id(self, contact_id: int) -> Optional[Contact]:
        result = await self._session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def list_by_campaign(self, campaign_id: int) -> list[Contact]:
        result = await self._session.execute(
            select(Contact)
            .where(Contact.campaign_id == campaign_id)
            .order_by(Contact.created_at)
        )
        return list(result.scalars().all())

    async def get_next_pending(self, campaign_id: int) -> Optional[Contact]:
        result = await self._session.execute(
            select(Contact)
            .where(
                Contact.campaign_id == campaign_id,
                Contact.state == ContactState.PENDING,
            )
            .order_by(Contact.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_waiting_since_before(self, cutoff: datetime) -> list[Contact]:
        result = await self._session.execute(
            select(Contact).where(
                Contact.state == ContactState.WAITING_RESPONSE,
                Contact.first_message_sent_at < cutoff,
            )
        )
        return list(result.scalars().all())

    async def find_by_phone(
        self, phone_normalized: str, campaign_id: int
    ) -> Optional[Contact]:
        result = await self._session.execute(
            select(Contact).where(
                Contact.phone_normalized == phone_normalized,
                Contact.campaign_id == campaign_id,
            )
        )
        return result.scalar_one_or_none()

    async def transition_state(
        self,
        contact_id: int,
        new_state: ContactState,
        *,
        phone_normalized: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        values: dict = {
            "state": new_state,
            "last_activity_at": datetime.now(timezone.utc),
        }
        if phone_normalized is not None:
            values["phone_normalized"] = phone_normalized
        if notes is not None:
            values["notes"] = notes
        await self._session.execute(
            update(Contact).where(Contact.id == contact_id).values(**values)
        )

    async def mark_first_message_sent(self, contact_id: int) -> None:
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(Contact)
            .where(Contact.id == contact_id)
            .values(
                state=ContactState.WAITING_RESPONSE,
                first_message_sent_at=now,
                last_activity_at=now,
            )
        )

    async def update_conversation(
        self, contact_id: int, conversation_json: str
    ) -> None:
        await self._session.execute(
            update(Contact)
            .where(Contact.id == contact_id)
            .values(
                conversation_json=conversation_json,
                last_activity_at=datetime.now(timezone.utc),
            )
        )

    async def set_manual_mode(self, contact_id: int, manual_mode: bool) -> None:
        await self._session.execute(
            update(Contact)
            .where(Contact.id == contact_id)
            .values(
                manual_mode=manual_mode,
                last_activity_at=datetime.now(timezone.utc),
            )
        )
