import os
from dotenv import load_dotenv
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from fastapi import status
from src.app import app
from src.core.agent_orchestrator import get_contact_info_tool_function, get_projects_tool_function, get_bio_tool_function, get_skills_tool_function, get_work_experience_tool_function, get_certifications_tool_function

# Load environment variables for tests
load_dotenv()
TEST_API_KEY = os.getenv("API_KEY")

if not TEST_API_KEY:
    pytest.skip("API_KEY not set in .env, skipping API key protected tests", allow_module_level=True)

@pytest_asyncio.fixture(scope="function") # to ensure fresh client/lifespan per test
async def client():    
    async with LifespanManager(app) as manager:        
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url=("http://127.0.0.1" + os.getenv('PORT', '8000'))) as ac:
            yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    # Health check does not require API key
    response = await client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert data["services"]["mongodb"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_chat_flow(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}

    # Step 1: Send first message to start a chat session
    response = await client.post("/api/v1/chat", json={"message": "Who is Lorenzo Maiuri?"}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    chat_id = data.get("chatId")
    assert chat_id is not None
    assert "message" in data
    assert "action" in data

    # Step 2: Send second message in the same chat (general query)
    response2 = await client.post("/api/v1/chat", json={"message": "Tell me about Lorenzo expertises.", "chatId": chat_id}, headers=headers)
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    assert data2["chatId"] == chat_id
    assert "message" in data2
    assert "action" in data2
    assert data2["action"]["action_type"] == "show_skills"
    
    # Step 3: Retrieve chat history
    history_response = await client.get(f"/api/v1/chat/{chat_id}/history", headers=headers)
    assert history_response.status_code == status.HTTP_200_OK
    history_data = history_response.json()
    assert history_data["chatId"] == chat_id
    messages = history_data["messages"]
    assert len(messages) >= 4
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"

    # Step 4: Delete the session
    delete_response = await client.delete(f"/api/v1/chat/{chat_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json()["message"] == "Session deleted successfully"

    # Step 5: Check that the session is deleted
    invalid_history = await client.get(f"/api/v1/chat/{chat_id}/history", headers=headers)
    assert invalid_history.status_code == status.HTTP_200_OK
    invalid_data = invalid_history.json()
    assert invalid_data["totalMessages"] == 0
    assert invalid_data["messages"] == []


@pytest.mark.asyncio
async def test_tool_get_contact_info(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        
    contact_queries = [
        "How can I contact Lorenzo Maiuri?",
    ]

    for i, query in enumerate(contact_queries):
        # Start a new chat for each query to ensure fresh agent state
        response = await client.post("/api/v1/chat", json={"message": query}, headers=headers)
        assert response.status_code == status.HTTP_200_OK, f"Failed for query: '{query}'"
        data = response.json()
        chat_id = data.get("chatId")
        
        assert chat_id is not None
        assert "message" in data
        assert "action" in data
        
        # Assert that the correct action type is returned
        assert data["action"]["action_type"] == "show_contact", \
            f"Expected 'show_contact' for query '{query}', got '{data['action']['action_type']}'"
        
        # Assert that the data matches the expected output from the tool function
        expected_contact_data = get_contact_info_tool_function()
        assert data["action"]["data"] == expected_contact_data, \
            f"Contact data mismatch for query '{query}'. Expected {expected_contact_data}, got {data['action']['data']}"
            
        # Optional: Delete session after each test for isolation, or do it once at the end
        await client.delete(f"/api/v1/chat/{chat_id}", headers=headers)
        
    print(f"\nSuccessfully tested {len(contact_queries)} 'get_contact_info' queries.")


@pytest.mark.asyncio
async def test_tool_get_projects(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    
    # Test cases that should trigger get_projects
    project_queries = [        
        "What projects has Lorenzo worked on?",
    ]

    for i, query in enumerate(project_queries):
        # Start a new chat for each query
        response = await client.post("/api/v1/chat", json={"message": query}, headers=headers)
        assert response.status_code == status.HTTP_200_OK, f"Failed for query: '{query}'"
        data = response.json()
        chat_id = data.get("chatId")
        
        assert chat_id is not None
        assert "message" in data
        assert "action" in data
        
        # Assert that the correct action type is returned
        assert data["action"]["action_type"] == "show_projects", \
            f"Expected 'show_projects' for query '{query}', got '{data['action']['action_type']}'"
        
        # Assert that the data matches the expected output from the tool function
        expected_projects_data = get_projects_tool_function()
        assert data["action"]["data"] == expected_projects_data, \
            f"Projects data mismatch for query '{query}'. Expected {expected_projects_data}, got {data['action']['data']}"
            
        # Optional: Delete session after each test for isolation
        await client.delete(f"/api/v1/chat/{chat_id}", headers=headers)

    print(f"\nSuccessfully tested {len(project_queries)} 'get_projects' queries.")

@pytest.mark.asyncio
async def test_tool_get_skills(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
        
    contact_queries = [
        "What can Lorenzo do?",
    ]

    for i, query in enumerate(contact_queries):
        # Start a new chat for each query to ensure fresh agent state
        response = await client.post("/api/v1/chat", json={"message": query}, headers=headers)
        assert response.status_code == status.HTTP_200_OK, f"Failed for query: '{query}'"
        data = response.json()
        chat_id = data.get("chatId")
        
        assert chat_id is not None
        assert "message" in data
        assert "action" in data
        
        # Assert that the correct action type is returned
        assert data["action"]["action_type"] == "show_skills", \
            f"Expected 'show_skills' for query '{query}', got '{data['action']['action_type']}'"
        
        # Assert that the data matches the expected output from the tool function
        expected_skills_data = get_skills_tool_function()
        assert data["action"]["data"] == expected_skills_data, \
            f"Skills data mismatch for query '{query}'. Expected {expected_skills_data}, got {data['action']['data']}"
            
        # Optional: Delete session after each test for isolation, or do it once at the end
        await client.delete(f"/api/v1/chat/{chat_id}", headers=headers)
        
    print(f"\nSuccessfully tested {len(contact_queries)} 'get_contact_info' queries.")

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    # Test chat endpoint without any authorization header
    response = await client.post("/api/v1/chat", json={"message": "Should be unauthorized"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or missing API Key"

    # Test chat endpoint with a wrong authorization header
    response = await client.post("/api/v1/chat", json={"message": "Should be unauthorized"}, headers={"Authorization": "Bearer WRONG_KEY"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or missing API Key"

    # Test history endpoint without authorization
    response = await client.get("/api/v1/chat/some_id/history")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or missing API Key"

    # Test delete endpoint without authorization
    response = await client.delete("/api/v1/chat/some_id")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid or missing API Key"


# @pytest.mark.asyncio
# async def test_rate_limit(client: AsyncClient):
#     headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    
#     # We need to know the configured limits to test this reliably
#     from app.core.config import Config
#     test_config = Config() # Load config for test values
    
#     # Send requests up to the limit
#     for i in range(test_config.rate_limit_requests):
#         response = await client.post("/api/v1/chat", json={"message": f"Test rate limit {i+1}"}, headers=headers)
#         assert response.status_code == status.HTTP_200_OK, f"Request {i+1} failed before rate limit"
        
#     # The next request should hit the rate limit
#     response = await client.post("/api/v1/chat", json={"message": "Test rate limit (exceed)"}, headers=headers)
#     assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
#     assert response.json()["detail"] == "Rate limit exceeded. Please wait before sending more messages."

#     # OPTIONAL: Wait for the window to reset and test again
#     # This makes the test slower but more comprehensive
#     # await asyncio.sleep(test_config.rate_limit_window + 1)
#     # response_after_wait = await client.post("/api/v1/chat", json={"message": "Test after wait"}, headers=headers)
#     # assert response_after_wait.status_code == status.HTTP_200_OK