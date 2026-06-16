[![License](https://img.shields.io/badge/license-AGPL%20V3-blue)](https://opensource.org/license/agpl-v3)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Profile-blue?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/maiurilorenzo)

# LorenzoBot — Backend

AI chatbot backend for [lorenzomaiuri.dev](https://www.lorenzomaiuri.dev). Answers questions about Lorenzo's projects, skills, availability, and contact — with real-time streaming, citation chips, and semantic search over case studies.

---

## Architecture

```
User message
    │
    ▼
RouterAgent  ──────────────────────────────────────────────────────
    │                                                              │
    ├──▶ ProjectAgent        search_projects, get_project_details, │
    │                        get_case_study, search_case_study_    │
    │                        content, recommend_similar_project    │
    │                                                              │
    ├──▶ TechnicalAgent      get_stack_info, get_core_stack,       │
    │                        get_certifications, get_education      │
    │                                                              │
    ├──▶ AvailabilityAgent   check_availability (Cal.com),         │
    │                        get_engagement_model                  │
    │                                                              │
    └──▶ ContactAgent        get_contact_info,                     │
                             trigger_contact_action          ◀─────┘
                                                      (bidirectional handoffs)

SSE stream → token | citation | action | handoff | tool_call | tool_result | done
```

Each agent has a dedicated system prompt (`prompts/`), its own tool set, and can hand off back to the router or to a peer agent mid-conversation. The frontend receives a typed SSE event stream — citation chips and contact modal triggers are embedded in the stream alongside the text tokens.

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Gemini 3.5 Flash (`gemini-3.5-flash`) |
| Agent framework | LlamaIndex `AgentWorkflow` + `ReActAgent` |
| API | FastAPI, `StreamingResponse` (SSE) |
| Session storage | Firestore Native (subcollection schema) |
| Vector search | Firestore Vector Search (`find_nearest`, `gemini-embedding-2`) |
| Booking | Cal.com API v2 |
| Observability | OpenTelemetry + Phoenix/Arize |
| Auth | Bearer token (`API_KEY`) + rate limiting |
| Package manager | uv |
| Container | Docker (python:3.11-slim + uv) |
| Infrastructure | Terraform + Google Cloud Run |
| CI/CD | GitHub Actions + Workload Identity Federation |

---

## API reference

All endpoints except `/health` require `Authorization: Bearer <API_KEY>`.

### v2 (current)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v2/chat/stream` | Streaming chat — Server-Sent Events |
| `GET` | `/api/v2/chat/{chatId}/history` | Retrieve session message history |
| `DELETE` | `/api/v2/chat/{chatId}` | Delete a session and all its messages |
| `GET` | `/api/v2/health` | Health check (no auth) |
| `GET` | `/api/v2/stats` | Session count |

### v1 (deprecated, maintained for backward compat)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | Synchronous chat — returns full response |
| `GET` | `/api/v1/chat/{chatId}/history` | History |
| `DELETE` | `/api/v1/chat/{chatId}` | Delete session |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/stats` | Stats |

### Streaming request / response

```
POST /api/v2/chat/stream
Authorization: Bearer <API_KEY>
Content-Type: application/json

{"chatId": "abc123" | null, "message": "What AI projects has Lorenzo built?"}
```

The response is a stream of SSE events:

```
event: meta
data: {"chatId": "abc123", "agent": "router_agent"}

event: handoff
data: {"from": "router_agent", "to": "project_agent"}

event: thinking
data: {"agent": "project_agent", "step": "calling search_projects"}

event: tool_call
data: {"tool": "search_projects", "input": {"category": "ai-agents"}}

event: citation
data: {"kind": "project", "slug": "ai-customer-support-chatbot", "label": "AI-Powered Customer Support Chatbot"}

event: tool_result
data: {"tool": "search_projects", "result_summary": "done"}

event: token
data: {"text": "Lorenzo has built several AI agent systems, including "}

event: token
data: {"text": "an end-to-end customer support chatbot..."}

event: action
data: {"action_type": "open_contact_modal", "payload": {}}

event: done
data: {"chatId": "abc123"}
```

**Citation kinds:** `project` | `case-study` | `certification` | `stack`

**Action types:** `open_contact_modal` | `scroll_to` | `show_projects`

---

## Project structure

```
.
├── data/                    # Static JSON/TXT data files (source of truth for all tools)
│   ├── projects.json        # 12 projects with slug, category, stack, description
│   ├── case_studies.json    # 3 deep-dive case studies (challenge, decisions, results)
│   ├── skills.json          # Tech skills by category
│   ├── certifications.json
│   ├── education.json
│   ├── engagement.json      # Work style, availability, engagement types
│   ├── contact.json
│   ├── work_experience.json
│   └── bio.txt
│
├── prompts/                 # System prompts — one file per agent
│   ├── router_agent.md
│   ├── project_agent.md
│   ├── technical_agent.md
│   ├── availability_agent.md
│   └── contact_agent.md
│
├── scripts/
│   ├── ingest.py            # Builds Firestore vector collections from data/
│   └── export_openapi.py    # Exports openapi.json for frontend type generation
│
├── src/
│   ├── app.py               # FastAPI app, lifespan, middleware
│   ├── api/
│   │   └── endpoints.py     # All routes + SSE event generator
│   └── core/
│       ├── agent_orchestrator.py   # AgentWorkflow: router + 4 specialists
│       ├── config.py               # Config from environment variables
│       ├── database.py             # Firestore AsyncClient (sessions)
│       ├── models.py               # Pydantic request/response models
│       ├── security.py             # API key validation, rate limiting
│       ├── services.py             # ChatbotService: session + history logic
│       ├── tools.py                # 12 tool functions (+ legacy v1 aliases)
│       └── vector_store.py         # Firestore vector search + embedding helper
│
├── tests/
│   └── test_chatbot.py      # Integration tests (live Firestore) + unit tests (tools)
│
├── infra/                   # Terraform — see infra/README.md
├── .github/workflows/       # CI (pre-commit + tests) + deploy + terraform
├── .pre-commit-config.yaml  # ruff, mypy, terraform_fmt/validate, osv-scanner
├── pyproject.toml           # Dependencies, ruff, mypy, pytest config
└── Dockerfile
```

---

## Local development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) — for Firestore access
- A GCP project with Firestore Native enabled

### 1. Clone and install

```bash
git clone https://github.com/lorenzomaiuri-dev/lorenzo-maiuri-chatbot.git
cd lorenzo-maiuri-chatbot
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required
API_KEY=any-secret-key-you-choose
GEMINI_API_KEY=your-google-ai-studio-key

# GCP — needed for Firestore
GCP_PROJECT_ID=your-gcp-project-id

# Cal.com booking (optional — tools degrade gracefully without it)
CALCOM_USERNAME=your-cal-com-username
CALCOM_API_KEY=your-cal-com-api-key
CALCOM_EVENT_SLUG=30min

# Observability (optional — skipped with a warning if not set)
PHOENIX_CLIENT_HEADERS=api_key=your-phoenix-key

# Server
PORT=8080
ENV=development
ALLOWED_ORIGINS=http://localhost:3000
```

Get a free `GEMINI_API_KEY` at [aistudio.google.com](https://aistudio.google.com/app/apikey).

### 3. Authenticate to GCP

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Firestore must exist in the project:

```bash
gcloud firestore databases create \
  --location=europe-west3 \
  --type=firestore-native
```

### 4. Install pre-commit hooks

```bash
uv run pre-commit install
```

This installs the hooks into `.git/hooks/pre-commit` so they run automatically on every `git commit`. On the first commit after install, pre-commit will download and cache the hook environments (ruff, mypy, terraform, osv-scanner) — this takes a minute but only happens once.

To run all hooks manually without committing:

```bash
uv run pre-commit run --all-files
```

### 5. Run the dev server

```bash
uv run uvicorn src.app:app --reload --port 8080
```

Interactive API docs: [http://localhost:8080/docs](http://localhost:8080/docs)

### 6. Vector search (optional)

The `search_case_study_content` and `recommend_similar_project` tools degrade gracefully to a text fallback when the vector index does not exist. To enable them fully:

**Create Firestore vector indexes (one-time):**

```bash
gcloud alpha firestore indexes composite create \
  --project=$GCP_PROJECT_ID \
  --collection-group=case_study_embeddings \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'

gcloud alpha firestore indexes composite create \
  --project=$GCP_PROJECT_ID \
  --collection-group=project_embeddings \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'
```

**Run the ingest pipeline:**

```bash
uv run scripts/ingest.py
```

This embeds all case study sections and project descriptions via `gemini-embedding-2` and upserts them into Firestore. Re-run whenever `data/case_studies.json` or `data/projects.json` changes.

---

## Testing

Tests require a live Firestore connection (`GCP_PROJECT_ID` + ADC). If `API_KEY` is not set the test module skips automatically.

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Unit tests only (no Firestore needed — direct tool function calls)
uv run pytest -k "not asyncio"
```

The test suite covers:
- Health checks (v1 + v2)
- Auth rejection (missing / wrong key)
- Tool unit tests — all 12 tools, including edge cases (not found, empty filters)
- SSE stream structure — first event is `meta`, last is `done`, `token` events present
- Project and contact query flows
- Session history and delete
- v1 backward compat

---

## Pre-commit hooks

```bash
uv run pre-commit install
```

Hooks run on every commit:

| Hook | What it checks |
|---|---|
| `ruff` | Lint + auto-fix (E, W, F, I, B rules) |
| `ruff-format` | Code formatting |
| `mypy` | Type checking (`src/`) |
| `terraform_fmt` | Formats all `.tf` files recursively |
| `terraform_validate` | Validates each changed module (init with `-backend=false`) |
| `osv-scanner` | Scans `uv.lock` for known CVEs |

Run all hooks manually:

```bash
uv run pre-commit run --all-files
```

---

## Scripts

### `scripts/ingest.py`

Builds Firestore vector collections for semantic search. Reads `data/case_studies.json` and `data/projects.json`, calls `gemini-embedding-2` for each document chunk, and upserts into Firestore `case_study_embeddings` and `project_embeddings` collections.

```bash
uv run scripts/ingest.py
```

Requires `GEMINI_API_KEY` and `GCP_PROJECT_ID` in `.env`.

### `scripts/export_openapi.py`

Exports the FastAPI OpenAPI schema to `openapi.json` for frontend TypeScript type generation.

```bash
uv run scripts/export_openapi.py

# Then on the frontend:
npx openapi-typescript openapi.json -o src/types/api.ts
```

---

## Data files

All tool responses are derived from static JSON/TXT files in `data/`. Updating these files is the primary way to keep the bot's knowledge current — no redeployment needed for content changes, except for semantic search (re-run `scripts/ingest.py` after changing `projects.json` or `case_studies.json`).

| File | Used by | Contents |
|---|---|---|
| `projects.json` | ProjectAgent | 12 projects — slug, category, stack, description, status |
| `case_studies.json` | ProjectAgent | 3 deep-dive case studies — challenge, approach, decisions, results |
| `skills.json` | TechnicalAgent | Skills grouped by category |
| `certifications.json` | TechnicalAgent | Professional certifications |
| `education.json` | TechnicalAgent | Academic background |
| `engagement.json` | AvailabilityAgent | Work style, timezone, engagement types |
| `contact.json` | ContactAgent | Email, LinkedIn, GitHub, etc. |
| `work_experience.json` | v1 legacy tool | Work history |
| `bio.txt` | v1 legacy tool | Short biography |

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_KEY` | Yes | — | Bearer token for all authenticated endpoints |
| `GEMINI_API_KEY` | Yes | — | Google AI Studio or Vertex AI key |
| `GCP_PROJECT_ID` | Yes | — | GCP project for Firestore |
| `GEMINI_MODEL` | No | `gemini-3.5-flash` | Gemini model ID |
| `GEMINI_TEMPERATURE` | No | `0.7` | LLM temperature |
| `GEMINI_MAX_TOKENS` | No | `2048` | Max output tokens |
| `CALCOM_USERNAME` | No | — | Cal.com username for booking |
| `CALCOM_API_KEY` | No | — | Cal.com API key |
| `CALCOM_EVENT_SLUG` | No | `30min` | Cal.com event type slug |
| `PHOENIX_CLIENT_HEADERS` | No | — | `api_key=…` header for Phoenix cloud |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS origins (comma-separated) |
| `PORT` | No | `8080` | Server port |
| `ENV` | No | `development` | `development` or `production` |
| `RATE_LIMIT_REQUESTS` | No | `30` | Requests per window |
| `RATE_LIMIT_WINDOW` | No | `60` | Window in seconds |

---

## Deployment

Infrastructure is fully managed with Terraform. See **[infra/README.md](infra/README.md)** for the complete guide covering:

- GCP resource provisioning (Cloud Run, Firestore, Artifact Registry, Secret Manager)
- Workload Identity Federation setup (no service account keys)
- GitHub Actions CI/CD pipeline
- Bootstrap steps and first deploy
- Free-tier analysis

CI/CD summary:
- **Push to `main`** → pre-commit checks → tests → Docker build → deploy to Cloud Run (manual approval gate)
- **PR with `infra/` changes** → `terraform plan` posted as PR comment
- **Merge `infra/` to `main`** → `terraform apply` (manual approval gate)

---

## License

AGPL-3.0 — see [LICENSE](LICENSE).

## Contact

- Email: [contact@lorenzomaiuri.dev](mailto:contact@lorenzomaiuri.dev)
- LinkedIn: [linkedin.com/in/maiurilorenzo](https://www.linkedin.com/in/maiurilorenzo/)
- GitHub: [github.com/lorenzomaiuri-dev](https://github.com/lorenzomaiuri-dev)
