import logging
from datetime import date, timedelta
from typing import Optional

from src.core.config import Config
from src.utils.utils import _read_data_file

logger = logging.getLogger(__name__)
config = Config()

# ── Project Agent tools ───────────────────────────────────────────────────────


def search_projects(
    category: Optional[str] = None,
    stack: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
) -> dict:
    """
    Searches Lorenzo's projects with optional filters.
    - category: one of 'ai-agents', 'nlp', 'data-engineering', 'web', 'mobile', 'computer-vision', 'mlops'
    - stack: any technology name (e.g. 'Python', 'FastAPI', 'LlamaIndex')
    - status: 'completed' or 'active'
    - type: 'personal' or 'professional'
    Returns a list of matching projects.
    """
    projects = _read_data_file("projects.json", is_json=True)
    if not isinstance(projects, list):
        return {"projects": [], "_citations": []}

    results = projects

    if category:
        results = [p for p in results if p.get("category", "").lower() == category.lower()]
    if stack:
        results = [
            p for p in results if any(stack.lower() in t.lower() for t in p.get("technologies", []))
        ]
    if status:
        results = [p for p in results if p.get("status", "").lower() == status.lower()]
    if type:
        results = [p for p in results if p.get("type", "").lower() == type.lower()]

    citations = [
        {"kind": "project", "slug": p["slug"], "label": p["title"]}
        for p in results
        if p.get("slug")
    ]
    logger.info(f"search_projects: {len(results)} results (category={category}, stack={stack})")
    return {"projects": results, "_citations": citations}


def get_project_details(slug: str) -> dict:
    """
    Returns full details for a specific project by its slug.
    Use this when the user asks about a specific project by name or wants to know more.
    """
    projects = _read_data_file("projects.json", is_json=True)
    if not isinstance(projects, list):
        return {"error": "Projects data unavailable"}

    project = next((p for p in projects if p.get("slug") == slug), None)
    if not project:
        return {
            "error": f"Project with slug '{slug}' not found. Use search_projects to find available slugs."
        }

    citations = [{"kind": "project", "slug": slug, "label": project["title"]}]
    logger.info(f"get_project_details: {slug}")
    return {"project": project, "_citations": citations}


def get_case_study(slug: str) -> dict:
    """
    Returns the structured case study for a project: challenge, approach, decisions, results, retrospective.
    Available for: 'ai-customer-support-chatbot', 'data-warehouse-modernization', 'gentleman-closet'.
    """
    case_studies = _read_data_file("case_studies.json", is_json=True)
    if not isinstance(case_studies, list):
        return {"error": "Case study data unavailable"}

    study = next((c for c in case_studies if c.get("slug") == slug), None)
    if not study:
        return {
            "error": f"No case study found for '{slug}'. Available slugs: ai-customer-support-chatbot, data-warehouse-modernization, gentleman-closet."
        }

    citations = [{"kind": "case-study", "slug": slug, "label": study["title"]}]
    logger.info(f"get_case_study: {slug}")
    return {"case_study": study, "_citations": citations}


async def search_case_study_content(query: str) -> dict:
    """
    Semantic search over Lorenzo's case study content: challenges, approach, decisions, results, retrospective.
    Use when the user asks about the depth behind a specific project — why certain choices were made,
    what problems were encountered, or what was learned. Returns the most relevant sections with citations.
    """
    from google.api_core.exceptions import FailedPrecondition

    from src.core.vector_store import vector_search

    try:
        docs = await vector_search("case_study_embeddings", query, n_results=3)
        chunks = []
        seen_slugs: set = set()
        citations = []
        for doc in docs:
            chunks.append(
                {
                    "content": doc.get("content", ""),
                    "section": doc.get("section", ""),
                    "slug": doc.get("slug", ""),
                }
            )
            if doc.get("slug") not in seen_slugs:
                seen_slugs.add(doc["slug"])
                citations.append(
                    {"kind": "case-study", "slug": doc["slug"], "label": doc.get("title", "")}
                )
        logger.info("search_case_study_content: %d chunks for query '%s'", len(chunks), query[:50])
        return {"chunks": chunks, "_citations": citations}
    except FailedPrecondition:
        logger.warning("search_case_study_content: Firestore vector index not ready")
        return {
            "message": "Semantic search index not ready. Use get_case_study with a specific slug.",
            "fallback": "Available slugs: ai-customer-support-chatbot, data-warehouse-modernization, gentleman-closet",
        }
    except Exception as e:
        logger.error("search_case_study_content error: %s", e)
        return {"error": "Search failed. Use get_case_study as a fallback."}


async def recommend_similar_project(description: str) -> dict:
    """
    Recommends Lorenzo's projects semantically similar to a given description.
    Use when the user describes a problem, domain, or use case and wants to know
    if Lorenzo has worked on something similar. Returns ranked matches with citations.
    """
    from google.api_core.exceptions import FailedPrecondition

    from src.core.vector_store import vector_search

    try:
        docs = await vector_search("project_embeddings", description, n_results=3)
        projects = []
        citations = []
        for doc in docs:
            projects.append(
                {
                    "slug": doc.get("slug", ""),
                    "title": doc.get("title", ""),
                    "category": doc.get("category", ""),
                    "summary": doc.get("content", "")[:300],
                }
            )
            citations.append(
                {"kind": "project", "slug": doc["slug"], "label": doc.get("title", "")}
            )
        logger.info(
            "recommend_similar_project: %d results for '%s'", len(projects), description[:50]
        )
        return {"similar_projects": projects, "_citations": citations}
    except FailedPrecondition:
        logger.warning("recommend_similar_project: Firestore vector index not ready")
        return {
            "message": "Semantic search not available. Use search_projects with category or stack filters.",
            "suggestion": "Try search_projects with the relevant stack or category.",
        }
    except Exception as e:
        logger.error("recommend_similar_project error: %s", e)
        return {"error": "Recommendation failed. Use search_projects as a fallback."}


# ── Technical Agent tools ─────────────────────────────────────────────────────


def get_stack_info(tech: str) -> dict:
    """
    Returns Lorenzo's experience with a specific technology or tool.
    Use this when the user asks about experience with a specific language, framework, or tool.
    """
    skills = _read_data_file("skills.json", is_json=True)
    if not isinstance(skills, dict):
        return {"error": "Skills data unavailable"}

    tech_lower = tech.lower()
    found_in = []

    for category, items in skills.items():
        if isinstance(items, list):
            matches = [item for item in items if tech_lower in item.lower()]
            if matches:
                found_in.append({"category": category, "entries": matches})

    if not found_in:
        return {
            "tech": tech,
            "found": False,
            "message": f"'{tech}' not found in Lorenzo's skills. This doesn't mean he hasn't used it — ask him directly via contact.",
        }

    citation = {"kind": "stack", "slug": tech_lower.replace(" ", "-"), "label": tech}
    logger.info(f"get_stack_info: {tech}")
    return {"tech": tech, "found": True, "categories": found_in, "_citations": [citation]}


def get_core_stack() -> dict:
    """
    Returns Lorenzo's primary tech stack and main areas of expertise.
    Use when the user asks for an overview of his skills or core technologies.
    """
    core = {
        "primary_languages": ["Python", "JavaScript/TypeScript", "C#"],
        "ai_ml": [
            "LlamaIndex",
            "LangChain",
            "Hugging Face Transformers",
            "OpenAI",
            "Gemini",
            "RAG",
            "AI Agents",
            "LLMs",
        ],
        "backend": ["FastAPI", "Flask", "ASP.NET Core"],
        "cloud": ["GCP", "AWS"],
        "databases": ["PostgreSQL", "MongoDB", "ChromaDB", "Redis"],
        "devops": ["Docker", "Kubernetes", "GitHub Actions", "OpenTelemetry"],
        "data_engineering": ["Apache Airflow", "Pandas", "ETL pipelines"],
        "focus_areas": [
            "LLM application development",
            "Multi-agent systems",
            "MLOps",
            "Data engineering",
        ],
    }
    citations = [
        {"kind": "stack", "slug": "python", "label": "Python"},
        {"kind": "stack", "slug": "llamaindex", "label": "LlamaIndex"},
        {"kind": "stack", "slug": "fastapi", "label": "FastAPI"},
    ]
    logger.info("get_core_stack called")
    return {"core_stack": core, "_citations": citations}


def get_certifications() -> dict:
    """
    Returns Lorenzo's professional certifications with years.
    Use when the user asks about certifications, credentials, or qualifications.
    """
    certs = _read_data_file("certifications.json", is_json=True)
    citations = [
        {"kind": "certification", "slug": f"cert-{i}", "label": c["name"]}
        for i, c in enumerate(certs)
        if isinstance(certs, list)
    ]
    logger.info("get_certifications called")
    return {"certifications": certs, "_citations": citations}


def get_education() -> dict:
    """
    Returns Lorenzo's educational background.
    Use when the user asks about his degree, university, or academic background.
    """
    education = _read_data_file("education.json", is_json=True)
    logger.info("get_education called")
    return {"education": education}


# ── Availability Agent tools ──────────────────────────────────────────────────


async def check_availability(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Checks Lorenzo's real-time availability for a 30-minute call via Cal.com.
    date_from and date_to should be in YYYY-MM-DD format (optional, defaults to next 7 days).
    Returns available time slots and a booking link.
    """
    import httpx

    if not config.calcom_username:
        return {
            "available": None,
            "message": "Booking not configured yet. Please reach out via email: contact@lorenzomaiuri.dev",
        }

    today = date.today()
    start = date_from or today.isoformat()
    end = date_to or (today + timedelta(days=7)).isoformat()
    booking_url = f"https://cal.com/{config.calcom_username}/{config.calcom_event_slug}"

    params = {
        "username": config.calcom_username,
        "eventTypeSlug": config.calcom_event_slug,
        "startTime": f"{start}T00:00:00Z",
        "endTime": f"{end}T23:59:59Z",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.cal.com/v2/slots/available", params=params)
            response.raise_for_status()
            data = response.json()

        slots = data.get("data", {}).get("slots", {})
        available_days = {day: times for day, times in slots.items() if times}

        if not available_days:
            return {
                "available": False,
                "period": f"{start} to {end}",
                "message": "No available slots in this period. Try a wider date range.",
                "booking_url": booking_url,
            }

        summary = [
            f"{day}: {len(times)} slot(s)" for day, times in list(available_days.items())[:5]
        ]
        logger.info(f"check_availability: {len(available_days)} days available")
        return {
            "available": True,
            "period": f"{start} to {end}",
            "available_days": summary,
            "booking_url": booking_url,
        }

    except httpx.HTTPError as e:
        logger.error(f"Cal.com API error: {e}")
        return {
            "available": None,
            "message": "Could not check availability right now. Use the link below to book directly.",
            "booking_url": booking_url,
        }


def get_engagement_model() -> dict:
    """
    Returns how Lorenzo works: engagement types, timezone, async-first style, preferred projects.
    Use when the user asks how Lorenzo works, what kind of projects he takes, or about his work style.
    """
    model = _read_data_file("engagement.json", is_json=True)
    logger.info("get_engagement_model called")
    return {"engagement_model": model}


# ── Contact Agent tools ───────────────────────────────────────────────────────


def get_contact_info() -> dict:
    """
    Returns Lorenzo's contact information: email, LinkedIn, GitHub, Hugging Face, Kaggle.
    Use when the user asks for contact details or specific profile links.
    """
    contact = _read_data_file("contact.json", is_json=True)
    logger.info("get_contact_info called")
    return {"contact": contact}


def trigger_contact_action() -> dict:
    """
    Opens the contact modal on the frontend.
    Use when the user explicitly wants to send Lorenzo a message or fill in the contact form.
    """
    logger.info("trigger_contact_action called")
    return {
        "message": "I've opened the contact form for you.",
        "_action": {
            "action_type": "open_contact_modal",
            "payload": {},
        },
    }


# ── Legacy aliases (Sprint 1 backward compat) ─────────────────────────────────


def get_contact_info_tool_function():
    """
    **Specifically provides Lorenzo Maiuri's direct contact details, like email, LinkedIn, GitHub, or portfolio link.**
    Useful when a user explicitly asks for ways to contact Lorenzo or his specific professional links.
    """
    return get_contact_info()


def get_projects_tool_function():
    """
    **Specifically lists and describes Lorenzo Maiuri's key projects with links.**
    Useful when a user explicitly asks to see Lorenzo's portfolio, specific project examples, or a list of his work.
    """
    return search_projects()


def get_bio_tool_function():
    """
    Provides a general biography or summary of the person of Lorenzo Maiuri.
    Useful when the user asks 'Who is Lorenzo?', 'Tell me about Lorenzo?', 'Tell me something about him?'.
    """
    return {"bio": _read_data_file("bio.txt")}


def get_skills_tool_function():
    """
    Provides a detailed list of Lorenzo Maiuri's technical skills and specializations.
    Useful when the user asks 'What are his skills?', 'What skills does Lorenzo have?', 'What can Lorenzo do?'.
    """
    return {"skills": _read_data_file("skills.json", is_json=True)}


def get_work_experience_tool_function():
    """
    Provides a summary of Lorenzo Maiuri's work and professional experiences.
    Useful when the user asks 'What is his work experience?', 'Where did Lorenzo work?'.
    """
    return {"experience": _read_data_file("work_experience.json", is_json=True)}


def get_certifications_tool_function():
    """
    Provides a list of Lorenzo Maiuri's professional and academic certifications.
    Useful when user asks 'What certifications does Lorenzo have?', 'Does he have any certifications?'.
    """
    return get_certifications()
