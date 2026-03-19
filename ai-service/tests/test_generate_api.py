"""Integration tests for the generation API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {settings.api_key_header: settings.api_key}

@pytest.fixture
def first_message_payload() -> dict:
    return {
        "commerce_name": "Bar El Sol",
        "system_prompt": "Sos un vendedor de páginas web para restaurantes.",
    }

@pytest.fixture
def reply_payload() -> dict:
    return {
        "commerce_name": "Bar El Sol",
        "system_prompt": "Sos un vendedor de páginas web para restaurantes.",
        "conversation": [
            {"role": "assistant", "content": "Hola, te contacto para ofrecerte..."},
            {"role": "user", "content": "¿Cuánto cuesta?"},
        ],
    }

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_first_message_requires_auth(first_message_payload):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/generate/first-message", json=first_message_payload)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_reply_requires_auth(reply_payload):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post("/api/generate/reply", json=reply_payload)
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_first_message_empty_commerce_name_rejected(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/generate/first-message",
            json={"commerce_name": "", "system_prompt": "Prompt válido de al menos 10 caracteres."},
            headers=auth_headers,
        )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_reply_invalid_role_rejected(auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/generate/reply",
            json={
                "commerce_name": "Bar",
                "system_prompt": "Prompt válido de al menos 10 caracteres.",
                "conversation": [{"role": "invalid", "content": "Hola"}],
            },
            headers=auth_headers,
        )
    assert resp.status_code == 422
