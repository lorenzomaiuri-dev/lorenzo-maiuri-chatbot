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
    type: str = Field(..., pattern=r"^(none|show_contact|send_email|show_projects)$")
    data: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    chatId: str
    message: str
    action: ActionData
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    chatId: str
    messages: List[Message]
    totalMessages: int
    