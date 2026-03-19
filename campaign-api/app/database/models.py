"""SQLAlchemy ORM models.

Two tables:
  campaigns  — one per outreach campaign
  contacts   — one per target commerce within a campaign
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.engine import Base
from app.domain.campaign.state_machine import ContactState

class Campaign(Base):
    """Represents a WhatsApp outreach campaign."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    auto_sales_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    wait_hours_no_reply: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    max_auto_messages: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

class Contact(Base):
    """Represents a single commerce contact within a campaign."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    commerce_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_normalized: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    state: Mapped[str] = mapped_column(
        String(50), default=ContactState.PENDING, nullable=False
    )
    first_message_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    conversation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manual_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="contacts"
    )
