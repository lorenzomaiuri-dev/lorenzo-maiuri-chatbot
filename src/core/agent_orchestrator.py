import logging

from llama_index.core.agent.workflow import AgentWorkflow, ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.google_genai import GoogleGenAI

from src.core.config import Config
from src.core.tools import (
    # AvailabilityAgent
    check_availability,
    get_case_study,
    get_certifications,
    # ContactAgent
    get_contact_info,
    get_core_stack,
    get_education,
    get_engagement_model,
    get_project_details,
    # TechnicalAgent
    get_stack_info,
    recommend_similar_project,
    search_case_study_content,
    # ProjectAgent
    search_projects,
    trigger_contact_action,
)
from src.utils.utils import load_prompt

logger = logging.getLogger(__name__)
config = Config()


def _llm() -> GoogleGenAI:
    return GoogleGenAI(
        api_key=config.gemini_api_key,
        model=f"models/{config.gemini_model}",
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


def _tool(fn, name: str) -> FunctionTool:
    return FunctionTool.from_defaults(fn=fn, name=name, description=fn.__doc__)


def get_main_agent_workflow() -> AgentWorkflow:
    llm = _llm()

    router = ReActAgent(
        name="router_agent",
        description="Routes the user's message to the right specialist agent.",
        system_prompt=load_prompt("router_agent"),
        tools=[],
        llm=llm,
        can_handoff_to=["project_agent", "technical_agent", "availability_agent", "contact_agent"],
    )

    project = ReActAgent(
        name="project_agent",
        description="Answers questions about Lorenzo's projects, portfolio, and case studies.",
        system_prompt=load_prompt("project_agent"),
        tools=[
            _tool(search_projects, "search_projects"),
            _tool(get_project_details, "get_project_details"),
            _tool(get_case_study, "get_case_study"),
            _tool(search_case_study_content, "search_case_study_content"),
            _tool(recommend_similar_project, "recommend_similar_project"),
        ],
        llm=llm,
        can_handoff_to=["router_agent", "technical_agent", "contact_agent"],
    )

    technical = ReActAgent(
        name="technical_agent",
        description="Answers questions about Lorenzo's technical skills, stack, education, and certifications.",
        system_prompt=load_prompt("technical_agent"),
        tools=[
            _tool(get_stack_info, "get_stack_info"),
            _tool(get_core_stack, "get_core_stack"),
            _tool(get_certifications, "get_certifications"),
            _tool(get_education, "get_education"),
        ],
        llm=llm,
        can_handoff_to=["router_agent", "project_agent", "availability_agent"],
    )

    availability = ReActAgent(
        name="availability_agent",
        description="Checks Lorenzo's availability for meetings and explains how he works.",
        system_prompt=load_prompt("availability_agent"),
        tools=[
            _tool(check_availability, "check_availability"),
            _tool(get_engagement_model, "get_engagement_model"),
        ],
        llm=llm,
        can_handoff_to=["router_agent", "contact_agent"],
    )

    contact = ReActAgent(
        name="contact_agent",
        description="Provides Lorenzo's contact information and opens the contact form.",
        system_prompt=load_prompt("contact_agent"),
        tools=[
            _tool(get_contact_info, "get_contact_info"),
            _tool(trigger_contact_action, "trigger_contact_action"),
        ],
        llm=llm,
        can_handoff_to=["router_agent", "availability_agent"],
    )

    workflow = AgentWorkflow(
        agents=[router, project, technical, availability, contact],
        root_agent="router_agent",
    )
    logger.info("Multi-agent AgentWorkflow initialized (router + 4 specialists)")
    return workflow
