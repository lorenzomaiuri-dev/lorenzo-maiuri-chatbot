import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import lru_cache

from llama_index.core import Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.llms import ChatMessage, MessageRole

from core.config import Config
from core.database import Mongo
from utils.constants import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
config = Config()

class EnhancedChatbotService:
    def __init__(self):
        self.llm = GoogleGenAI(
            api_key=config.gemini_api_key,
            model=f"models/{config.gemini_model}",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        Settings.llm = self.llm
        
        self.chat_engines: Dict[str, SimpleChatEngine] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_or_create_chat_engine(self, chat_id: str, mongo: Mongo) -> SimpleChatEngine:
        """Get or create a chat engine with memory for the session."""
        if chat_id not in self.chat_engines:
            memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
                tokenizer_fn=Settings.tokenizer,
            )
            
            await self._load_history_to_memory(chat_id, memory, mongo)
            
            chat_engine = SimpleChatEngine.from_defaults(
                llm=self.llm,
                memory=memory,
                system_prompt=SYSTEM_PROMPT,
                verbose=True
            )
            
            self.chat_engines[chat_id] = chat_engine
            self.session_locks[chat_id] = asyncio.Lock()
        
        return self.chat_engines[chat_id]
    
    async def _load_history_to_memory(self, chat_id: str, memory: ChatMemoryBuffer, mongo: Mongo):
        """Load chat history from database to memory."""
        try:
            session = await mongo.sessions.find_one({"chatId": chat_id})
            if session and "messages" in session:
                messages = session["messages"][-config.max_memory_messages:]
                
                for msg in messages:
                    role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    chat_message = ChatMessage(role=role, content=msg["content"])
                    memory.put(chat_message)
                    
        except Exception as e:
            logger.error(f"Error loading history for {chat_id}: {e}", exc_info=True)
    
    async def create_or_get_session(self, mongo: Mongo, chat_id: Optional[str] = None) -> str:
        """Create or retrieve a chat session."""
        if not chat_id:
            chat_id = str(uuid.uuid4())
        
        try:
            existing = await mongo.sessions.find_one({"chatId": chat_id})
            if not existing:
                session_data = {
                    "chatId": chat_id,
                    "messages": [],
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "messageCount": 0
                }
                await mongo.sessions.insert_one(session_data)
                logger.info(f"Created new session: {chat_id}")
            
            return chat_id
            
        except Exception as e:
            logger.error(f"Error creating/getting session {chat_id}: {e}", exc_info=True)
            raise
    
    async def save_message(self, chat_id: str, role: str, content: str, mongo: Mongo):
        """Save a single message to the database."""
        try:
            message_data = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            }
            
            await mongo.sessions.update_one(
                {"chatId": chat_id},
                {
                    "$push": {"messages": message_data},
                    "$set": {"updatedAt": datetime.utcnow()},
                    "$inc": {"messageCount": 1}
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving message for {chat_id}: {e}", exc_info=True)
            raise
    
    async def generate_response(self, chat_id: str, user_message: str, mongo: Mongo) -> Dict[str, Any]:
        """Generate response using LlamaIndex chat engine."""
        
        if chat_id not in self.session_locks:
            self.session_locks[chat_id] = asyncio.Lock()
        
        async with self.session_locks[chat_id]:
            try:
                chat_engine = await self.get_or_create_chat_engine(chat_id, mongo)
                
                await self.save_message(chat_id, "user", user_message, mongo)
                
                response = await chat_engine.achat(user_message)
                
                parsed_response = self._parse_bot_response(str(response))
                
                await self.save_message(chat_id, "assistant", parsed_response["message"], mongo)
                
                return parsed_response
                
            except Exception as e:
                logger.error(f"Error generating response for {chat_id}: {e}", exc_info=True)
                fallback_response = {
                    "message": "Mi dispiace, ho riscontrato un problema tecnico. Puoi riprovare o contattare Lorenzo direttamente per assistenza.",
                    "action": {"type": "show_contact", "data": {}}
                }
                try:
                    await self.save_message(chat_id, "assistant", fallback_response["message"], mongo)
                except Exception as save_e:
                    logger.error(f"Failed to save fallback message: {save_e}")
                return fallback_response
    
    def _parse_bot_response(self, response_text: str) -> Dict[str, Any]:
        """Parse bot response and extract action if present."""
        try:            
            action_type = "none"
            action_data = {}
            
            response_lower = response_text.lower()
            
            if any(phrase in response_lower for phrase in ["contattare lorenzo", "contatto", "email", "scrivere"]):
                action_type = "show_contact"
            elif any(phrase in response_lower for phrase in ["progetti", "portfolio", "lavori", "esempi"]):
                action_type = "show_projects"
            elif "email" in response_lower and "invia" in response_lower:
                action_type = "send_email"
            
            return {
                "message": response_text.strip(),
                "action": {
                    "type": action_type,
                    "data": action_data
                }
            }
            
        except Exception as e:
            logger.warning(f"Error parsing response: {e}", exc_info=True)
            return {
                "message": response_text.strip(),
                "action": {"type": "none", "data": {}}
            }
    
    async def get_chat_history(self, chat_id: str, mongo: Mongo, limit: int = 50) -> List[Dict]:
        """Get chat history from database."""
        try:
            session = await mongo.sessions.find_one(
                {"chatId": chat_id},
                {"messages": {"$slice": -limit}}
            )
            return session.get("messages", []) if session else []
            
        except Exception as e:
            logger.error(f"Error getting history for {chat_id}: {e}", exc_info=True)
            return []
    
    async def delete_session(self, chat_id: str, mongo: Mongo) -> bool:
        """Delete a chat session."""
        try:
            result = await mongo.sessions.delete_one({"chatId": chat_id})
            
            if chat_id in self.chat_engines:
                del self.chat_engines[chat_id]
            if chat_id in self.session_locks:
                del self.session_locks[chat_id]
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting session {chat_id}: {e}", exc_info=True)
            return False


@lru_cache() 
def get_chatbot_service() -> EnhancedChatbotService:
    """
    Provides a singleton instance of EnhancedChatbotService.
    This service manages its own LLM and in-memory chat engines.
    """
    return EnhancedChatbotService()
