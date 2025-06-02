import logging
from typing import List

from llama_index.core.agent.workflow import AgentWorkflow, ReActAgent
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.tools import FunctionTool

from src.core.config import Config
from src.core.tools import get_contact_info_tool_function, get_projects_tool_function, get_bio_tool_function, get_skills_tool_function, get_work_experience_tool_function, get_certifications_tool_function
from src.utils.constants import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
config = Config()


def get_main_agent_workflow() -> AgentWorkflow:
    """
    Initializes and returns the main AgentWorkflow for the chatbot.
    This workflow orchestrates different specialized agents.
    """
    
    llm = GoogleGenAI(
            api_key=config.gemini_api_key,
            model=f"models/{config.gemini_model}",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )

    # 'General Chat' Agent
    # This agent will handle general conversation and also use basic tools.
    general_chat_tools: List[FunctionTool] = [
        FunctionTool.from_defaults(fn=get_contact_info_tool_function, name="get_contact_info", description=get_contact_info_tool_function.__doc__),
        FunctionTool.from_defaults(fn=get_projects_tool_function, name="get_projects", description=get_projects_tool_function.__doc__),
        FunctionTool.from_defaults(fn=get_bio_tool_function, name="get_bio", description=get_bio_tool_function.__doc__),   
        FunctionTool.from_defaults(fn=get_skills_tool_function, name="get_skills", description=get_skills_tool_function.__doc__),
        FunctionTool.from_defaults(fn=get_work_experience_tool_function, name="get_work_experience", description=get_work_experience_tool_function.__doc__),
        FunctionTool.from_defaults(fn=get_certifications_tool_function, name="get_certifications", description=get_certifications_tool_function.__doc__),
    ]

    general_agent = ReActAgent(
        name="general_chat_agent",
        description="Handles general conversation, provides contact information, and information about projects.",
        system_prompt=(SYSTEM_PROMPT),
        tools=general_chat_tools,
        llm=llm
    )

    # Other specialized agents (e.g., for future RAG, QA, etc.)

    # Create and return the AgentWorkflow
    # 'root_agent' determines which agent gets the first pass at the user's message.
    main_workflow = AgentWorkflow(
        agents=[general_agent],
        root_agent="general_chat_agent"
    )
    
    logger.info("AgentWorkflow initialized with 'general_chat_agent' as root.")
    return main_workflow
