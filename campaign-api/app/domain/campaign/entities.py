"""Pydantic schemas for campaigns and contacts (request / response DTOs).

Applying SOLID — Single Responsibility: each class represents one DTO.
Pydantic provides OWASP A03/A04 protection via input validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.campaign.state_machine import ContactState

class ContactInput(BaseModel):
    """A single commerce contact provided by the frontend."""

    commerce_name: str = Field(..., min_length=1, max_length=255)
    phone_raw: str = Field(..., min_length=1, max_length=100)

    @field_validator("phone_raw")
    @classmethod
    def strip_phone(cls, v: str) -> str:
        return v.strip()

class CampaignCreate(BaseModel):
    """Payload to create a new campaign (contacts are uploaded separately via /ingest)."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    system_prompt: str = Field(..., min_length=10)
    auto_sales_enabled: bool = False
    wait_hours_no_reply: int = Field(24, ge=1, le=168)
    max_auto_messages: int = Field(5, ge=1, le=20)
    contacts: list[ContactInput] = Field(default_factory=list)

class CampaignResponse(BaseModel):
    """Campaign read model returned to the client."""

    id: int
    name: str
    description: str | None = None
    system_prompt: str
    auto_sales_enabled: bool
    wait_hours_no_reply: int = 24
    max_auto_messages: int = 5
    status: str
    created_at: datetime
    total_contacts: int = 0
    contacts_by_state: dict[str, int] = Field(default_factory=dict)

class IngestResponse(BaseModel):
    """Summary returned after a CSV ingest."""

    total_rows: int
    contacts_loaded: int
    contacts_no_phone: int
    contacts_duplicate: int

    model_config = {"from_attributes": True}

class CampaignStatusUpdate(BaseModel):
    """Payload to pause, resume or complete a campaign."""

    status: str = Field(..., pattern="^(active|paused|completed)$")

class ContactResponse(BaseModel):
    """Contact read model returned to the client."""

    id: int
    campaign_id: int
    commerce_name: str
    phone_raw: str
    phone_normalized: str | None
    state: ContactState
    first_message_sent_at: datetime | None
    last_activity_at: datetime | None
    notes: str | None
    manual_mode: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}

class ContactPatchRequest(BaseModel):
    """Payload to update mutable contact fields."""

    manual_mode: bool | None = None

class ManualMessageRequest(BaseModel):
    """Payload to send a manual message to a contact."""

    message: str = Field(..., min_length=1, max_length=4096)

class ConversationMessage(BaseModel):
    """Single message entry in a contact's conversation history."""

    role: str
    content: str
    timestamp: datetime

class ContactConversationResponse(BaseModel):
    """Full conversation history for a contact."""

    contact_id: int
    commerce_name: str
    state: ContactState
    messages: list[ConversationMessage]

class IncomingWhatsAppMessage(BaseModel):
    """Payload pushed by whatsapp-gateway when a customer replies."""

    phone: str = Field(..., description="E.164 normalized phone number")
    message: str = Field(..., min_length=1)
    timestamp: datetime
    extra: dict[str, Any] = Field(default_factory=dict)
