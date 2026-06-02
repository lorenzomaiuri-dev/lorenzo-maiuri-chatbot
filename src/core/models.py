from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=4000)
    timestamp: Optional[datetime] = None

    @field_validator("content")
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty or only whitespace")
        return v.strip()


# ── v1 models (deprecated endpoint) ──────────────────────────────────────────


class ChatRequest(BaseModel):
    chatId: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty or only whitespace")
        return v.strip()


class ActionData(BaseModel):
    action_type: str = Field(
        ...,
        pattern=r"^(display_message|show_contact|show_projects|show_bio|show_skills|show_experience|show_certifications|open_contact_modal|scroll_to)$",
    )
    data: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    chatId: str
    message: str
    action: ActionData
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    chatId: str
    messages: List[Message]
    totalMessages: int


# ── v2 models ─────────────────────────────────────────────────────────────────


class ChatStreamRequest(BaseModel):
    chatId: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty or only whitespace")
        return v.strip()
