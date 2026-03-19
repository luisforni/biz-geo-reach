"""Integration tests for the campaigns and contacts API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {settings.api_key_header: settings.api_key}

@pytest.fixture
def campaign_payload() -> dict:
    return {
        "name": "Test Campaign",
        "system_prompt": "Sos un vendedor de páginas web para restaurantes.",
        "auto_sale_enabled": False,
        "contacts": [
            {"commerce_name": "Bar El Sol", "phone_raw": "+5491112345678"},
            {"commerce_name": "Café Luna", "phone_raw": "+5491187654321"},
        ],
    }

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_list_campaigns_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/campaigns")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_campaign_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/campaigns", json={})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_wrong_api_key_returns_401():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/campaigns", headers={settings.api_key_header: "wrong-key"}
        )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_campaigns_empty(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/campaigns", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_campaign_invalid_payload(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/campaigns",
            json={"name": ""},
            headers=auth_headers,
        )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_nonexistent_campaign_returns_404(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/campaigns/99999", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_status_invalid_value(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            "/api/campaigns/1/status",
            json={"status": "invalid-status"},
            headers=auth_headers,
        )
    assert response.status_code == 422
