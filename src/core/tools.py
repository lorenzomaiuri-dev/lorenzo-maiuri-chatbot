import logging
from src.utils.utils import _read_data_file

logger = logging.getLogger(__name__)

def get_contact_info_tool_function():
    """
    **Specifically provides Lorenzo Maiuri's direct contact details, like email, LinkedIn, GitHub, or portfolio link.**
    Useful when a user explicitly asks for ways to contact Lorenzo or his specific professional links.
    """
    logger.info("Executing tool: get_contact_info_tool_function")
    return {"contact": _read_data_file("contact.json", is_json=True)}

def get_projects_tool_function():
    """
    **Specifically lists and describes Lorenzo Maiuri's key projects with links.**
    Useful when a user explicitly asks to see Lorenzo's portfolio, specific project examples, or a list of his work.
    """
    logger.info("Executing tool: get_projects_tool_function")
    return {"projects": _read_data_file("projects.json", is_json=True)}

def get_bio_tool_function():
    """
    Provides a general biography or summary of the person of Lorenzo Maiuri.
    Useful when the user asks 'Who is Lorenzo?', 'Tell me about Lorenzo?', 'Tell me something about him?'.
    """
    logger.info("Executing tool: get_bio_tool_function")
    return {"bio": _read_data_file("bio.txt")}

def get_skills_tool_function():
    """
    Provides a detailed list of Lorenzo Maiuri's technical skills and specializations.
    Useful when the user asks 'What are his skills?', 'What skills does Lorenzo have?', 'What can Lorenzo do?'.
    """
    logger.info("Executing tool: get_skills_tool_function")
    return {"skills": _read_data_file("skills.json", is_json=True)}

def get_work_experience_tool_function():
    """
    Provides a summary of Lorenzo Maiuri's work and professional experiences.
    Useful when the user asks 'What is his work experience?', 'Where did Lorenzo work?', 'Tell me about his professional experiences?'.
    """
    logger.info("Executing tool: get_lorenzo_experience_tool_function")
    return {"experience": _read_data_file("work_experience.json", is_json=True)}

def get_certifications_tool_function():
    """
    Provides a list of Lorenzo Maiuri's professional and academic certifications.
    Useful when user asks 'What certifications does Lorenzo have?', 'Does he have any certifications?'.
    """
    logger.info("Executing tool: get_certifications_tool_function")
    return {"certifications": _read_data_file("certifications.json", is_json=True)}