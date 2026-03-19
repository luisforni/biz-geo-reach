"""HTTP adapter for the whatsapp-gateway service.

Pattern: Adapter — translates domain calls into HTTP requests so the rest
of the application stays unaware of transport details.
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PhoneValidationResult:
    phone_normalized: str
    has_whatsapp: bool

class WhatsAppGatewayError(Exception):
    """Raised when the whatsapp-gateway returns an error or is unreachable."""

class WhatsAppClient:
    """Async HTTP client for the whatsapp-gateway service."""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url or settings.whatsapp_gateway_url
        self._api_key = api_key or settings.whatsapp_gateway_api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def validate_phone(self, phone: str) -> PhoneValidationResult:
        """Check whether an E.164 phone number has an active WhatsApp account."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/phone/validate",
                    json={"phone": phone},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return PhoneValidationResult(
                    phone_normalized=data["phone_normalized"],
                    has_whatsapp=data["has_whatsapp"],
                )
            except httpx.HTTPStatusError as exc:
                logger.error("whatsapp-gateway validate error: %s", exc)
                raise WhatsAppGatewayError(str(exc)) from exc
            except httpx.RequestError as exc:
                logger.error("whatsapp-gateway unreachable: %s", exc)
                raise WhatsAppGatewayError(str(exc)) from exc

    async def send_message(self, phone: str, message: str) -> None:
        """Send a text message to a WhatsApp number."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/messages/send",
                    json={"phone": phone, "message": message},
                    headers=self._headers(),
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("whatsapp-gateway send error: %s", exc)
                raise WhatsAppGatewayError(str(exc)) from exc
            except httpx.RequestError as exc:
                logger.error("whatsapp-gateway unreachable: %s", exc)
                raise WhatsAppGatewayError(str(exc)) from exc
