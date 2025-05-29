from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime
import logging

from core.database import Mongo
from core.models import ChatRequest, ChatResponse, ChatHistoryResponse, Message, ActionData
from core.services import EnhancedChatbotService, get_chatbot_service
from core.security import rate_limited_api_key, validate_api_key
from core.database import get_mongo
from core.config import Config

logger = logging.getLogger(__name__)
router = APIRouter()

config = Config()

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limited_api_key)])
async def chat_endpoint(
    request_data: ChatRequest,
    background_tasks: BackgroundTasks,
    chatbot_service: EnhancedChatbotService = Depends(get_chatbot_service),
    mongo: Mongo = Depends(get_mongo)
):
    """Enhanced chat endpoint with proper error handling."""
            
    try:
        chat_id = await chatbot_service.create_or_get_session(mongo, request_data.chatId)
        bot_response = await chatbot_service.generate_response(chat_id, request_data.message, mongo)
        
        return ChatResponse(
            chatId=chat_id,
            message=bot_response["message"],
            action=ActionData(**bot_response["action"]),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/chat/{chat_id}/history", response_model=ChatHistoryResponse, dependencies=[Depends(validate_api_key)])
async def get_chat_history_endpoint(chat_id: str, limit: int = 50, mongo: Mongo = Depends(get_mongo), chatbot_service: EnhancedChatbotService = Depends(get_chatbot_service),):
    """Get chat history for a session."""
    try:
        limit = min(limit, 100)
        
        messages_data = await chatbot_service.get_chat_history(chat_id, mongo, limit)
        
        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp")
            )
            for msg in messages_data
        ]
        
        return ChatHistoryResponse(
            chatId=chat_id,
            messages=messages,
            totalMessages=len(messages)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving chat history")

@router.delete("/chat/{chat_id}", dependencies=[Depends(validate_api_key)])
async def delete_chat_session(chat_id: str, mongo: Mongo = Depends(get_mongo), chatbot_service: EnhancedChatbotService = Depends(get_chatbot_service),):
    """Delete a chat session."""
    try:
        success = await chatbot_service.delete_session(chat_id, mongo)
        
        if success:
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting session")

@router.get("/health")
async def health_check(mongo: Mongo = Depends(get_mongo)):
    """Enhanced health check."""
    from core.database import mongodb_client_instance # Access global client
    mongo_status = "unhealthy"
    if mongodb_client_instance:
        try:
            await mongodb_client_instance.admin.command('ping')
            mongo_status = "healthy"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}", exc_info=True)
    
    return {
        "status": "healthy" if mongo_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow(),
        "services": {
            "mongodb": mongo_status,
            "llm": "healthy" # Assuming LLM connection is implicitly healthy if API key is present
        },
        "version": "2.0.0"
    }

@router.get("/stats")
async def get_stats(mongo: Mongo = Depends(get_mongo), chatbot_service: EnhancedChatbotService = Depends(get_chatbot_service),):
    """Get basic API statistics."""
    try:
        total_sessions = await mongo.sessions.count_documents({})
        active_sessions = len(chatbot_service.chat_engines) # This is in-memory, so only for this instance
        
        return {
            "totalSessions": total_sessions,
            "activeSessions": active_sessions,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving statistics")
    