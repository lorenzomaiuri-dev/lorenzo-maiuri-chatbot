import logging
import uuid
from typing import Any, Dict, List, Optional

from google.cloud.firestore import SERVER_TIMESTAMP, AsyncClient, Increment
from llama_index.core.llms import ChatMessage, MessageRole

from src.core.config import Config
from src.core.tools import (
    get_contact_info_tool_function,
    get_projects_tool_function,
    get_skills_tool_function,
)

logger = logging.getLogger(__name__)
config = Config()

_SESSIONS = "chat_sessions"
_MESSAGES = "messages"


class ChatbotService:
    def __init__(self, db: AsyncClient):
        self.db = db

    # ── session management ────────────────────────────────────────────────────

    async def get_or_create_session(self, chat_id: Optional[str]) -> str:
        if chat_id:
            doc = await self.db.collection(_SESSIONS).document(chat_id).get()
            if doc.exists:
                return chat_id

        new_id = str(uuid.uuid4())
        await (
            self.db.collection(_SESSIONS)
            .document(new_id)
            .set(
                {
                    "created_at": SERVER_TIMESTAMP,
                    "updated_at": SERVER_TIMESTAMP,
                    "last_message_preview": "",
                    "message_count": 0,
                }
            )
        )
        logger.info(f"New session created: {new_id}")
        return new_id

    async def save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
        tool_calls: Optional[List] = None,
        citations: Optional[List] = None,
        actions: Optional[List] = None,
    ) -> None:
        await (
            self.db.collection(_SESSIONS)
            .document(chat_id)
            .collection(_MESSAGES)
            .add(
                {
                    "role": role,
                    "content": content,
                    "agent": agent,
                    "tool_calls": tool_calls,
                    "citations": citations,
                    "actions": actions,
                    "timestamp": SERVER_TIMESTAMP,
                }
            )
        )
        await (
            self.db.collection(_SESSIONS)
            .document(chat_id)
            .update(
                {
                    "updated_at": SERVER_TIMESTAMP,
                    "last_message_preview": content[:100],
                    "message_count": Increment(1),
                }
            )
        )

    async def get_history(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        session_doc = await self.db.collection(_SESSIONS).document(chat_id).get()
        if not session_doc.exists:
            return []

        query = (
            self.db.collection(_SESSIONS)
            .document(chat_id)
            .collection(_MESSAGES)
            .order_by("timestamp")
            .limit(min(limit, 100))
        )
        docs = await query.get()
        return [doc.to_dict() for doc in docs]

    async def delete_session(self, chat_id: str) -> bool:
        session_ref = self.db.collection(_SESSIONS).document(chat_id)
        session_doc = await session_ref.get()
        if not session_doc.exists:
            return False

        messages_ref = session_ref.collection(_MESSAGES)
        async for doc in messages_ref.stream():
            await doc.reference.delete()

        await session_ref.delete()
        logger.info(f"Session deleted: {chat_id}")
        return True

    async def count_sessions(self) -> int:
        count = 0
        async for _ in self.db.collection(_SESSIONS).stream():
            count += 1
        return count

    # ── history ↔ LlamaIndex format ───────────────────────────────────────────

    def build_llm_history(self, messages: List[Dict[str, Any]]) -> List[ChatMessage]:
        history = []
        for msg in messages[-config.max_memory_messages :]:
            role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
            content = msg.get("content", "")
            if content:
                history.append(ChatMessage(role=role, content=content))
        return history

    # ── v1 sync response (deprecated) ────────────────────────────────────────

    async def generate_response(self, chat_id: str, user_message: str) -> Dict[str, Any]:
        from src.core.agent_orchestrator import get_main_agent_workflow
        from src.core.models import ActionData

        history_data = await self.get_history(chat_id)
        llm_history = self.build_llm_history(history_data)

        agent_workflow = get_main_agent_workflow()
        bot_response_text = ""
        action_data_dict = ActionData(action_type="display_message", data=None).model_dump()

        try:
            handler = agent_workflow.run(user_msg=user_message, chat_history=llm_history)
            final_response = await handler

            if hasattr(final_response, "response") and final_response.response is not None:
                resp = final_response.response
                bot_response_text = resp.content if hasattr(resp, "content") else str(resp)
            else:
                bot_response_text = "I received an empty response. Please try again."

            if final_response.tool_calls:
                tool_name = final_response.tool_calls[0].tool_name
                if tool_name == "get_contact_info":
                    action_data_dict = ActionData(
                        action_type="show_contact",
                        data=get_contact_info_tool_function(),
                    ).model_dump()
                elif tool_name == "get_projects":
                    action_data_dict = ActionData(
                        action_type="show_projects",
                        data=get_projects_tool_function(),
                    ).model_dump()
                elif tool_name == "get_skills":
                    action_data_dict = ActionData(
                        action_type="show_skills",
                        data=get_skills_tool_function(),
                    ).model_dump()

        except Exception as e:
            logger.error(f"Agent error for {chat_id}: {e}", exc_info=True)
            bot_response_text = "I'm having trouble right now. Please try again later."
            action_data_dict = ActionData(action_type="display_message", data=None).model_dump()

        await self.save_message(chat_id, "user", user_message)
        await self.save_message(chat_id, "assistant", bot_response_text, agent="main")

        return {
            "chatId": chat_id,
            "message": bot_response_text,
            "action": action_data_dict,
        }
