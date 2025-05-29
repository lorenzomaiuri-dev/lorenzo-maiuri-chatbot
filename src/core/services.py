import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import lru_cache

from llama_index.core.llms import ChatMessage, MessageRole

from core.agent_orchestrator import get_main_agent_workflow
from core.models import ActionData, Message
from core.config import Config
from core.database import Mongo
from core.tools import get_contact_info_tool_function, get_projects_tool_function, get_bio_tool_function, get_skills_tool_function, get_work_experience_tool_function, get_certifications_tool_function

logger = logging.getLogger(__name__)
config = Config()

class EnhancedChatbotService:
    def __init__(self):
        pass
    
    async def create_or_get_session(self, mongo: Mongo, chat_id: Optional[str] = None) -> str:
        """Create or retrieve a chat session."""
        
        try:
            if chat_id:
                session_doc = await mongo.sessions.find_one({"chatId": chat_id})
                if session_doc:
                    return chat_id
            
            new_chat_id = str(uuid.uuid4())
            await mongo.sessions.insert_one({"chatId": new_chat_id, "messages": [], "created_at": datetime.utcnow()})
            return new_chat_id
            
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
    
    async def generate_response(self, chat_id: str, user_message: str, mongo: Mongo) -> Dict[str, Any]: # Changed type hint
        logger.info(f"Generating response for chat_id: {chat_id}")

        # Retrieve chat history from MongoDB
        session_doc = await mongo.sessions.find_one({"chatId": chat_id})
        if not session_doc:
            logger.warning(f"Session {chat_id} not found during response generation.")
            return {
                "chatId": chat_id,
                "message": "I couldn't find your chat session. Please try starting a new conversation.",
                "action": ActionData(action_type="display_message", data={"type": "error"}).model_dump()
            }

        # Convert history to ChatMessage format for LlamaIndex
        history = [
            ChatMessage(role=MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT, content=msg["content"])
            for msg in session_doc.get("messages", [])
        ]
        
        agent_workflow = get_main_agent_workflow()
        
        bot_response_text = ""
        action_data_dict = ActionData(action_type="display_message", data=None).model_dump() # Default action

        try:
            handler = agent_workflow.run(user_msg=user_message, chat_history=history)
            final_agent_response = await handler # Await to get the final AgentChatResponse

            if hasattr(final_agent_response, 'response') and final_agent_response.response is not None:
                if isinstance(final_agent_response.response, ChatMessage):
                    bot_response_text = final_agent_response.response.content
                else:
                    bot_response_text = str(final_agent_response.response)
            else:
                bot_response_text = "I received an empty response from the assistant."
            
            
            if final_agent_response.tool_calls:                
                tool_call = final_agent_response.tool_calls[0] # Get the first tool call
                tool_name = tool_call.tool_name
                
                if tool_name == "get_contact_info":
                    # Manually call the tool function to get the structured data for the frontend
                    tool_output_data = get_contact_info_tool_function()
                    action_data_dict = ActionData(action_type="show_contact", data=tool_output_data).model_dump()
                    if not bot_response_text: # Fallback
                        bot_response_text = "Here is how you can contact Lorenzo Maiuri:"

                elif tool_name == "get_projects":
                    tool_output_data = get_projects_tool_function()
                    action_data_dict = ActionData(action_type="show_projects", data=tool_output_data).model_dump()
                    if not bot_response_text: # Fallback
                        bot_response_text = "Here are some of Lorenzo Maiuri's key projects:"

                elif tool_name == "get_skills":
                    tool_output_data = get_skills_tool_function()
                    action_data_dict = ActionData(action_type="show_skills", data=tool_output_data).model_dump()
                    if not bot_response_text: # Fallback
                        bot_response_text = "Here are some of Lorenzo Maiuri's key skills:"
                
                else:
                    logger.warning(f"Agent called unknown tool: {tool_name}. Returning generic message.")
                    action_data_dict = ActionData(action_type="display_message", data={"type": "info"}).model_dump()

            else:
                # No tool call
                action_data_dict = ActionData(action_type="display_message", data={"type": "info"}).model_dump()

        except Exception as e:
            logger.error(f"Error during agent workflow execution for {chat_id}: {e}", exc_info=True)
            # Fallback
            bot_response_text = "I'm having a little trouble understanding that right now. Can I help you by providing Lorenzo's contact information?"
            action_data_dict = ActionData(action_type="show_contact", data=get_contact_info_tool_function()).model_dump()
        
        current_history = session_doc.get("messages", [])
        current_history.append(Message(role="user", content=user_message, timestamp=datetime.utcnow()).model_dump())
        current_history.append(Message(role="assistant", content=bot_response_text, timestamp=datetime.utcnow()).model_dump())

        await mongo.sessions.update_one(
            {"chatId": chat_id},
            {"$set": {"messages": current_history}}
        )
        logger.info(f"History updated for chat_id: {chat_id}")

        return {
            "chatId": chat_id,
            "message": bot_response_text,
            "action": action_data_dict
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
