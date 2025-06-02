[![License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

# 🤖 LorenzoBot — Lorenzo Maiuri's Intelligent Chatbot

This repository contains the backend for the AI assistant featured on [Lorenzo Maiuri's website](https://www.lorenzomaiuri.dev/). The chatbot is designed to provide visitors with accurate, up-to-date information about Lorenzo's background, skills, projects, and contact details, using advanced AI and modular software architecture.

## ✨ Features

### 🎯 Focused, Secure AI Assistant

- **Personalized Scope:** Only answers questions about Lorenzo Maiuri, his work, skills, projects, and contact information.
- **Language Awareness:** Automatically responds in the same language as the user's message (supports English as well as Italian and other languages).
- **Honest & Concise:** Never invents information; always provides clear, professional, and friendly responses.
- **Off-topic Handling:** Politely redirects users if their questions are unrelated to Lorenzo.

### 🧠 Multi-Agent, Tool-Enabled Reasoning

- **ReAct Pattern:** Uses the Reasoning + Acting (ReAct) approach for step-by-step problem solving.
- **Tool Calling:** Dynamically invokes backend tools to fetch structured data (e.g., contact info, project list, skills).
- **Extensible Agents:** Architecture supports adding more specialized agents or tools in the future.

### 🔄 Session-Based Memory

- **Persistent Chat Sessions:** Each conversation is tracked by a unique `chatId`, with full message history stored in MongoDB.
- **Frontend Actions:** Bot responses include structured action data, enabling the frontend to trigger custom UI updates (e.g., show contact form, display project cards).

### 🛡️ Security & Reliability

- **API Key Authentication:** All endpoints (except health check) require a valid API key.
- **Rate Limiting:** Prevents abuse by limiting the number of requests per user within a time window.
- **Security Headers:** Adds HTTP security headers to all responses.
- **Health & Stats Endpoints:** Provides endpoints for health checks and basic usage statistics.

### 📊 Observability & Monitoring

- **OpenTelemetry Integration:** Traces LlamaIndex agent and tool calls for advanced monitoring (Phoenix/Arize).
- **Structured Logging:** All actions and errors are logged for debugging and analytics.

## 🏗️ Architecture Overview

- **LlamaIndex Agent:** Orchestrates the conversation, decides when to call tools, and generates responses using Google's Gemini LLM.
- **Tools:** Python functions that fetch and return structured data from local files (JSON/TXT) for skills, projects, bio, certifications, etc.
- **MongoDB:** Stores chat sessions and message history for each user.
- **API Layer:** Exposes endpoints for chat, history, session management, health, and stats.

## 🧰 Tech Stack

| Layer         | Technology / Library                                      |
|---------------|----------------------------------------------------------|
| LLM           | [Gemini](https://ai.google.dev/gemini-api/docs)          |
| Agent Framework | [LlamaIndex](https://www.llamaindex.ai/)               |
| API           | [FastAPI](https://fastapi.tiangolo.com/)                 |
| Database      | [MongoDB](https://www.mongodb.com/)                      |
| Async Client  | [httpx](https://www.python-httpx.org/)                   |
| Auth & Security | FastAPI Security, HTTP Headers, Rate Limiting          |
| Observability | [Phoenix/Arize](https://arize.com/phoenix/) + OpenTelemetry |
| Containerization | Docker                                                |
| Testing       | [pytest](https://docs.pytest.org/), [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |
| Environment   | Python 3.11+, [python-dotenv](https://pypi.org/project/python-dotenv/) |

## 🚀 API Endpoints

- `POST /api/v1/chat` — Send a message, get a response and action (requires API key)
- `GET /api/v1/chat/{chat_id}/history` — Retrieve chat history (requires API key)
- `DELETE /api/v1/chat/{chat_id}` — Delete a chat session (requires API key)
- `GET /api/v1/health` — Health check (no auth required)
- `GET /api/v1/stats` — Basic usage statistics (requires API key)

All endpoints (except health) require an `Authorization: Bearer <API_KEY>` header.

## 🛠️ How It Works

1. **User sends a message** via the website.
2. **FastAPI backend** receives the message, checks authentication and rate limits.
3. **Agent workflow** (LlamaIndex + Gemini) processes the message, optionally calls a tool for structured data.
4. **Tool functions** fetch data from local files (e.g., `data/contact.json`, `data/projects.json`).
5. **Response** is returned with both a message and an action (e.g., show contact info, display projects).
6. **Frontend** uses the action data to update the UI accordingly.

## 📦 Running Locally

1. **Clone the repo** and install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

2. **Set up your `.env` file** with required API keys and config (see `.env.example`).
3. **Start MongoDB** (local or Atlas).
4. **Run the server:**

   ```sh
   uvicorn src.app:app --reload
   ```

5. **Run tests:**

   ```sh
   pytest
   ```

## 📝 Customization & Extensibility

- **Add new tools:** Implement new Python functions in `src/core/tools.py` and register them in the agent workflow.
- **Extend agent logic:** Modify `src/core/agent_orchestrator.py` to add more agents or change routing logic.
- **Frontend integration:** Use the `action` field in API responses to trigger custom UI behaviors.

## 📬 Contact

Interested in working together or want to know more?

- Email: [maiurilorenzo@gmail.com](mailto:maiurilorenzo@gmail.com)
- LinkedIn: [linkedin.com/in/maiurilorenzo](https://www.linkedin.com/in/maiurilorenzo/)
- GitHub: [github.com/lorenzomaiuri-dev](https://github.com/lorenzomaiuri-dev)

## 🙏 Acknowledgements

Thanks to the open-source community and all contributors to the libraries and tools that power this project.

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE) for details.

<!-- LINKS & IMAGES -->
[license-shield]: https://img.shields.io/badge/license-AGPL%20V3-blue
[license-url]: https://opensource.org/license/agpl-v3
[linkedin-shield]: https://img.shields.io/badge/LinkedIn-Profile-blue?logo=linkedin&logoColor=white
[linkedin-url]: https://www.linkedin.com/in/maiurilorenzo
