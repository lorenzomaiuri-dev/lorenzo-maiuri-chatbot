from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=4000)
    timestamp: Optional[datetime] = None
    
    @field_validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty or only whitespace')
        return v.strip()

class ChatRequest(BaseModel):
    chatId: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    
    @field_validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or only whitespace')
        return v.strip()

class ActionData(BaseModel):
    """
    Represents an action to be performed by the frontend based on bot's response.
    Can be a generic message display or a specific tool-triggered action.
    """
    action_type: str = Field(..., pattern=r"^(display_message|show_contact|show_projects|show_bio|show_skills|show_experience|show_certifications)$", description="Type of action")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional payload for the action, e.g., contact details or project list.")

class ChatResponse(BaseModel):
    chatId: str
    message: str
    action: ActionData
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    chatId: str
    messages: List[Message]
    totalMessages: int
    