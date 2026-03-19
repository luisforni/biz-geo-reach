"""Campaign CRUD endpoints."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_db_session
from app.domain.campaign.entities import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatusUpdate,
    IngestResponse,
)
from app.domain.campaign.service import CampaignService, get_campaign_service
from app.middleware.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

def _svc(session: AsyncSession = Depends(get_db_session)) -> CampaignService:
    return get_campaign_service(session)

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_campaign(
    payload: CampaignCreate,
    svc: CampaignService = Depends(_svc),
) -> CampaignResponse:
    """Create a new campaign and enqueue its contacts for processing."""
    campaign = await svc.create_campaign(payload)
    logger.info("Campaign created: id=%d name=%r", campaign.id, campaign.name)
    return campaign

@router.get(
    "",
    response_model=list[CampaignResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_campaigns(
    svc: CampaignService = Depends(_svc),
) -> list[CampaignResponse]:
    """List all campaigns."""
    return await svc.list_campaigns()

@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_campaign(
    campaign_id: int,
    svc: CampaignService = Depends(_svc),
) -> CampaignResponse:
    """Get a single campaign by ID."""
    campaign = await svc.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    return campaign

@router.post(
    "/{campaign_id}/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_api_key)],
)
async def ingest_contacts(
    campaign_id: int,
    file: UploadFile = File(..., description="CSV file with columns: Nombre, Teléfono"),
    svc: CampaignService = Depends(_svc),
) -> IngestResponse:
    """Upload a CSV file and append its contacts to an existing campaign."""
    campaign = await svc.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    csv_bytes = await file.read()
    result = await svc.ingest_contacts_csv(campaign_id, csv_bytes)
    logger.info(
        "Ingest campaign %d: loaded=%d no_phone=%d duplicate=%d",
        campaign_id,
        result.contacts_loaded,
        result.contacts_no_phone,
        result.contacts_duplicate,
    )
    return result

@router.post(
    "/{campaign_id}/start",
    response_model=CampaignResponse,
    dependencies=[Depends(require_api_key)],
)
async def start_campaign(
    campaign_id: int,
    svc: CampaignService = Depends(_svc),
) -> CampaignResponse:
    """Transition a campaign from 'draft' to 'active' so the worker picks it up."""
    campaign = await svc.update_campaign_status(campaign_id, "active")
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    logger.info("Campaign %d started", campaign_id)
    return campaign

@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    dependencies=[Depends(require_api_key)],
)
async def update_campaign_status(
    campaign_id: int,
    payload: CampaignStatusUpdate,
    svc: CampaignService = Depends(_svc),
) -> CampaignResponse:
    """Pause, resume or complete a campaign."""
    campaign = await svc.update_campaign_status(campaign_id, payload.status)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    logger.info("Campaign %d status → %s", campaign_id, payload.status)
    return campaign
