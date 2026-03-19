"""Pydantic schemas for AI generation requests and responses.

OWASP A03 — Injection: all inputs validated and length-capped
before they are embedded in prompts sent to the AI model.
"""

from pydantic import BaseModel, Field

class ConversationMessage(BaseModel):
    """Single message entry from the campaign-service conversation history."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4_096)
    timestamp: str = Field(default="")

class FirstMessageRequest(BaseModel):
    """Request body for POST /generate/first-message."""

    commerce_name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=10, max_length=4_096)

class ReplyRequest(BaseModel):
    """Request body for POST /generate/reply."""

    commerce_name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=10, max_length=4_096)
    conversation: list[ConversationMessage] = Field(..., min_length=1, max_length=50)

class MessageResponse(BaseModel):
    """Unified response body for both generation endpoints."""

    message: str
