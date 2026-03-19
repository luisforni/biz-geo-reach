"""Aggregates all API routers into a single mount point."""

from fastapi import APIRouter

from app.api.campaigns import router as campaigns_router
from app.api.contacts import router as contacts_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter()

api_router.include_router(campaigns_router)
api_router.include_router(contacts_router)
api_router.include_router(webhooks_router)
