"""Campaign service: core business logic.

SOLID principles applied:
  S — one class, one purpose: orchestrate campaigns and contacts
  D — depends on abstract repository interfaces, not SQLAlchemy directly

Pattern: Service Layer — sits between HTTP handlers and repositories,
keeping controllers thin and business rules testable in isolation.
"""

import csv
import io
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repository import (
    AbstractCampaignRepository,
    AbstractContactRepository,
    SQLiteCampaignRepository,
    SQLiteContactRepository,
)
from app.domain.campaign.entities import (
    CampaignCreate,
    CampaignResponse,
    ContactInput,
    ContactResponse,
    IngestResponse,
)

class CampaignService:
    """Orchestrates campaign creation and contact management.

    Receives repository instances via constructor injection so the
    concrete backend (SQLite, PostgreSQL, …) can be swapped in tests.
    """

    def __init__(
        self,
        campaign_repo: AbstractCampaignRepository,
        contact_repo: AbstractContactRepository,
    ) -> None:
        self._campaigns = campaign_repo
        self._contacts = contact_repo

    async def create_campaign(self, payload: CampaignCreate) -> CampaignResponse:
        """Persist a new campaign and optionally bulk-insert contacts."""
        campaign = await self._campaigns.create(payload)
        contacts = []
        if payload.contacts:
            contacts = await self._contacts.bulk_create(campaign.id, payload.contacts)
        return self._build_response(campaign, contacts)

    async def ingest_contacts_csv(
        self, campaign_id: int, csv_bytes: bytes
    ) -> IngestResponse:
        """Parse a CSV file and bulk-insert contacts into an existing campaign.

        Expected columns (first two are used; extras are ignored):
            Nombre, Teléfono, ...
        A BOM (U+FEFF) prefix is stripped automatically.
        """
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        total_rows = 0
        contacts_no_phone = 0
        contacts_duplicate = 0
        to_insert: list[ContactInput] = []
        seen_phones: set[str] = set()

        for row in reader:
            total_rows += 1
            name = (row.get("Nombre") or "").strip()
            phone = (row.get("Teléfono") or "").strip()

            if not phone:
                contacts_no_phone += 1
                continue

            if phone in seen_phones:
                contacts_duplicate += 1
                continue

            seen_phones.add(phone)
            to_insert.append(
                ContactInput(
                    commerce_name=name or "(sin nombre)",
                    phone_raw=phone,
                )
            )

        if to_insert:
            await self._contacts.bulk_create(campaign_id, to_insert)

        return IngestResponse(
            total_rows=total_rows,
            contacts_loaded=len(to_insert),
            contacts_no_phone=contacts_no_phone,
            contacts_duplicate=contacts_duplicate,
        )

    async def get_campaign(self, campaign_id: int) -> CampaignResponse | None:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            return None
        return self._build_response(campaign, campaign.contacts)

    async def list_campaigns(self) -> list[CampaignResponse]:
        campaigns = await self._campaigns.list_all()
        return [self._build_response(c, c.contacts) for c in campaigns]

    async def update_campaign_status(
        self, campaign_id: int, status: str
    ) -> CampaignResponse | None:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            return None
        await self._campaigns.update_status(campaign_id, status)
        campaign.status = status
        return self._build_response(campaign, campaign.contacts)

    async def list_contacts(self, campaign_id: int) -> list[ContactResponse]:
        contacts = await self._contacts.list_by_campaign(campaign_id)
        return [ContactResponse.model_validate(c) for c in contacts]

    @staticmethod
    def _build_response(campaign, contacts) -> CampaignResponse:
        by_state = Counter(c.state for c in contacts)
        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            system_prompt=campaign.system_prompt,
            auto_sales_enabled=campaign.auto_sales_enabled,
            wait_hours_no_reply=campaign.wait_hours_no_reply,
            max_auto_messages=campaign.max_auto_messages,
            status=campaign.status,
            created_at=campaign.created_at,
            total_contacts=len(contacts),
            contacts_by_state=dict(by_state),
        )

def get_campaign_service(session: AsyncSession) -> CampaignService:
    """Factory / FastAPI dependency that wires concrete repositories."""
    return CampaignService(
        campaign_repo=SQLiteCampaignRepository(session),
        contact_repo=SQLiteContactRepository(session),
    )
