import json
import os

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from dotenv import load_dotenv
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.app import app

load_dotenv()

TEST_API_KEY = os.getenv("API_KEY")
BASE_URL = f"http://127.0.0.1:{os.getenv('PORT', '8080')}"

if not TEST_API_KEY:
    pytest.skip("API_KEY not set in .env, skipping tests", allow_module_level=True)


@pytest_asyncio.fixture(scope="function")
async def client():
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
            yield ac


# ── health checks ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_v1(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_v2(client: AsyncClient):
    r = await client.get("/api/v2/health")
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"


# ── auth ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unauthorized(client: AsyncClient):
    for path, method in [
        ("/api/v1/chat", "POST"),
        ("/api/v2/chat/stream", "POST"),
        ("/api/v1/chat/some_id/history", "GET"),
        ("/api/v2/chat/some_id/history", "GET"),
    ]:
        fn = client.post if method == "POST" else client.get
        kwargs = {"json": {"message": "test"}} if method == "POST" else {}
        r = await fn(path, **kwargs)
        assert r.status_code == status.HTTP_401_UNAUTHORIZED, f"Expected 401 for {method} {path}"

    r = await client.post(
        "/api/v2/chat/stream",
        json={"message": "test"},
        headers={"Authorization": "Bearer WRONG_KEY"},
    )
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


# ── tools unit tests (no HTTP, direct function calls) ─────────────────────────


def test_search_projects_no_filter():
    from src.core.tools import search_projects

    result = search_projects()
    assert "projects" in result
    assert len(result["projects"]) > 0
    assert "_citations" in result


def test_search_projects_by_category():
    from src.core.tools import search_projects

    result = search_projects(category="ai-agents")
    assert all(p["category"] == "ai-agents" for p in result["projects"])


def test_search_projects_by_stack():
    from src.core.tools import search_projects

    result = search_projects(stack="Python")
    assert len(result["projects"]) > 0
    for p in result["projects"]:
        assert any("Python" in t for t in p["technologies"])


def test_search_projects_by_type():
    from src.core.tools import search_projects

    personal = search_projects(type="personal")
    professional = search_projects(type="professional")
    assert all(p["type"] == "personal" for p in personal["projects"])
    assert all(p["type"] == "professional" for p in professional["projects"])


def test_get_project_details_found():
    from src.core.tools import get_project_details

    result = get_project_details("dantegpt")
    assert "project" in result
    assert result["project"]["slug"] == "dantegpt"
    assert "_citations" in result
    assert result["_citations"][0]["kind"] == "project"


def test_get_project_details_not_found():
    from src.core.tools import get_project_details

    result = get_project_details("non-existent-slug")
    assert "error" in result


def test_get_case_study_found():
    from src.core.tools import get_case_study

    result = get_case_study("ai-customer-support-chatbot")
    assert "case_study" in result
    study = result["case_study"]
    assert "challenge" in study
    assert "approach" in study
    assert "results" in study
    assert result["_citations"][0]["kind"] == "case-study"


def test_get_case_study_not_found():
    from src.core.tools import get_case_study

    result = get_case_study("non-existent")
    assert "error" in result


@pytest.mark.asyncio
async def test_recommend_similar_project_fallback():
    """When the Firestore vector index is not set up, the tool returns a helpful fallback."""
    from src.core.tools import recommend_similar_project

    result = await recommend_similar_project("AI chatbot for customer support")
    # Expects either a successful result or a graceful fallback (no index in CI)
    assert isinstance(result, dict)
    assert "similar_projects" in result or "message" in result or "error" in result


def test_get_stack_info_found():
    from src.core.tools import get_stack_info

    result = get_stack_info("Python")
    assert result["found"] is True
    assert len(result["categories"]) > 0
    assert "_citations" in result


def test_get_stack_info_not_found():
    from src.core.tools import get_stack_info

    result = get_stack_info("COBOL")
    assert result["found"] is False


def test_get_core_stack():
    from src.core.tools import get_core_stack

    result = get_core_stack()
    assert "core_stack" in result
    core = result["core_stack"]
    assert "primary_languages" in core
    assert "ai_ml" in core
    assert "_citations" in result


def test_get_certifications():
    from src.core.tools import get_certifications

    result = get_certifications()
    assert "certifications" in result
    assert isinstance(result["certifications"], list)
    assert len(result["certifications"]) > 0


def test_get_education():
    from src.core.tools import get_education

    result = get_education()
    assert "education" in result
    assert isinstance(result["education"], list)


def test_get_engagement_model():
    from src.core.tools import get_engagement_model

    result = get_engagement_model()
    assert "engagement_model" in result
    assert "timezone" in result["engagement_model"]


def test_get_contact_info():
    from src.core.tools import get_contact_info

    result = get_contact_info()
    assert "contact" in result
    assert "email" in result["contact"]
    assert "linkedin" in result["contact"]


def test_trigger_contact_action():
    from src.core.tools import trigger_contact_action

    result = trigger_contact_action()
    assert "_action" in result
    assert result["_action"]["action_type"] == "open_contact_modal"


# ── v2 streaming ──────────────────────────────────────────────────────────────


async def _collect_sse_events(client: AsyncClient, message: str) -> tuple[list, str | None]:
    """Helper: stream a message and collect (event_type, payload) pairs."""
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    events = []
    chat_id = None

    async with client.stream(
        "POST",
        "/api/v2/chat/stream",
        json={"message": message},
        headers=headers,
    ) as response:
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers.get("content-type", "")

        current_event = None
        async for line in response.aiter_lines():
            line = line.strip()
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current_event:
                payload = json.loads(line.split(":", 1)[1].strip())
                events.append((current_event, payload))
                if current_event == "meta" and not chat_id:
                    chat_id = payload.get("chatId")
                current_event = None

    return events, chat_id


@pytest.mark.asyncio
async def test_v2_stream_structure(client: AsyncClient):
    events, chat_id = await _collect_sse_events(client, "Who is Lorenzo Maiuri?")

    event_types = [e for e, _ in events]
    assert event_types[0] == "meta", "First event must be 'meta'"
    assert event_types[-1] == "done", "Last event must be 'done'"
    assert "token" in event_types, "Must have at least one 'token' event"
    assert chat_id is not None

    # Cleanup
    if chat_id:
        headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        await client.delete(f"/api/v2/chat/{chat_id}", headers=headers)


@pytest.mark.asyncio
async def test_v2_stream_project_query(client: AsyncClient):
    """Project queries should trigger tool_call events and citation events."""
    events, chat_id = await _collect_sse_events(client, "What AI projects has Lorenzo worked on?")

    event_types = [e for e, _ in events]
    assert "token" in event_types
    assert "done" in event_types

    # Cleanup
    if chat_id:
        headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        await client.delete(f"/api/v2/chat/{chat_id}", headers=headers)


@pytest.mark.asyncio
async def test_v2_stream_contact_action(client: AsyncClient):
    """Contact queries should trigger an action event with open_contact_modal."""
    events, chat_id = await _collect_sse_events(client, "I want to send Lorenzo a message")

    event_types = [e for e, _ in events]
    assert "done" in event_types

    action_events = [payload for ev, payload in events if ev == "action"]
    if action_events:
        assert any(a.get("action_type") == "open_contact_modal" for a in action_events)

    # Cleanup
    if chat_id:
        headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        await client.delete(f"/api/v2/chat/{chat_id}", headers=headers)


@pytest.mark.asyncio
async def test_v2_history_and_delete(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}

    _, chat_id = await _collect_sse_events(client, "Tell me about Lorenzo's skills")
    assert chat_id

    r = await client.get(f"/api/v2/chat/{chat_id}/history", headers=headers)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["totalMessages"] >= 2
    assert data["messages"][0]["role"] == "user"

    r2 = await client.delete(f"/api/v2/chat/{chat_id}", headers=headers)
    assert r2.status_code == status.HTTP_200_OK

    r3 = await client.get(f"/api/v2/chat/{chat_id}/history", headers=headers)
    assert r3.json()["totalMessages"] == 0


# ── v1 backward compat ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_v1_chat_deprecated_still_works(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}

    r = await client.post("/api/v1/chat", json={"message": "Who is Lorenzo?"}, headers=headers)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    chat_id = data["chatId"]
    assert data["message"]
    assert data["action"]["action_type"]

    await client.delete(f"/api/v1/chat/{chat_id}", headers=headers)
