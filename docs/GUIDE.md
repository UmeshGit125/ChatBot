# College Chatbot - Developer Guide

A natural language chatbot that translates English, Hindi, and Hinglish questions into SQL queries against a college operations database, returning smartly formatted results.

---

## Project Structure

```
college-chatbot/
├── app/
│   ├── main.py                      # FastAPI entrypoint, lifespan, CORS, global error handler
│   ├── api/
│   │   ├── chat.py                  # POST /api/chat - main chat endpoint
│   │   └── logs.py                  # GET /api/logs - query log viewer
│   ├── core/
│   │   ├── config.py                # Pydantic Settings - all env config
│   │   ├── pipeline.py              # NL→SQL orchestration (the core flow)
│   │   ├── models.py                # Pydantic models (ChatRequest, ChatResponse, PipelineResult)
│   │   ├── conversation.py          # In-memory conversation state for clarification flows
│   │   ├── logger.py                # JSON-lines query logger for auditing
│   │   ├── rate_limiter.py          # Sliding-window rate limiter
│   │   └── week_utils.py            # Week boundary calculations for trend queries
│   ├── llm/
│   │   ├── base.py                  # BaseLLMProvider abstract class (the swap interface)
│   │   ├── gemini_provider.py       # Google Gemini implementation with retry
│   │   ├── factory.py               # Provider factory (reads LLM_PROVIDER env var)
│   │   └── prompts/
│   │       └── templates.py         # All prompt templates (classification, SQL gen, trends, etc.)
│   ├── db/
│   │   ├── connection.py            # Async SQLAlchemy engine, query executor, mock DB init
│   │   ├── mock_schema.sql          # DDL for all 16 tables
│   │   └── seed_data.sql            # Realistic sample data (25 students, 2 centers, etc.)
│   ├── schema/
│   │   ├── introspector.py          # Live DB metadata reader (PRAGMA / information_schema)
│   │   ├── annotations.yaml         # Curated domain groupings, table/column descriptions
│   │   └── context_builder.py       # Merges introspection + annotations → LLM prompt context
│   ├── guardrails/
│   │   └── sql_validator.py         # SELECT-only enforcement (sqlparse-based)
│   └── formatter/
│       └── response_formatter.py    # Smart response formatting (tables, summaries, fallback)
├── streamlit_app/
│   └── app.py                       # Streamlit chat UI
├── tests/
│   ├── test_benchmark.py            # 30+ domain coverage queries (all 8 domains)
│   ├── test_guardrails.py           # SQL validator tests
│   ├── test_formatter.py            # Response formatter tests
│   ├── test_pipeline.py             # Pipeline integration tests (mocked LLM)
│   └── test_schema.py              # Schema introspection + context builder tests
├── docs/
│   └── GUIDE.md                     # This file
├── .env.example                     # Template for environment variables
├── .env                             # Local environment (gitignored in production)
├── requirements.txt                 # Python dependencies (pip fallback)
├── pyproject.toml                   # Project config + dependencies (uv)
├── uv.lock                          # Locked dependency versions
├── Dockerfile                       # Backend container image
├── Dockerfile.streamlit             # Streamlit UI container image
├── docker-compose.yml               # Multi-container orchestration
└── pytest.ini                       # Pytest configuration
```

---

## Full Request Flow

```
User Question (English/Hindi/Hinglish)
         │
         ▼
┌─────────────────────────────────────┐
│  POST /api/chat                     │
│  ├── Input validation (length)      │
│  ├── Rate limit check               │
│  └── Conversation context lookup    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Pipeline (app/core/pipeline.py)    │
│                                     │
│  1. Classify Domain                 │
│     LLM determines: attendance,     │
│     academics, coding, etc.         │
│                                     │
│  2. Build Schema Context            │
│     Load only relevant tables       │
│     from annotations + introspect   │
│                                     │
│  3. Assess Ambiguity                │
│     If unclear → return clarifying  │
│     question (skip SQL generation)  │
│                                     │
│  4. Generate SQL                    │
│     LLM creates SELECT query with   │
│     schema context. Uses trend      │
│     prompt if comparison detected.  │
│                                     │
│  5. Validate SQL                    │
│     sqlparse checks: single stmt,   │
│     SELECT only, no forbidden ops   │
│     If invalid → retry once         │
│                                     │
│  6. Execute Query                   │
│     Run against DB (SQLite/Postgres)│
│     with statement_timeout          │
│                                     │
│  7. Return PipelineResult           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Response Formatter                 │
│  ├── Single value → natural sentence│
│  ├── Multi-row → summary + table   │
│  └── Empty → friendly message      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Log query + Return ChatResponse    │
│  { answer, sql, domain, row_count } │
└─────────────────────────────────────┘
```

---

## Running Locally

### Prerequisites

- **Python 3.11+**
- **Node.js 18+ and npm** (required to run the Next.js frontend locally)
- A **[Google Gemini API key](https://aistudio.google.com/apikey)**

### Option 1: Running with Docker (Recommended & Easiest)

No Python or Node.js installation is required. Docker builds and orchestrates all containers automatically:

```bash
# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Build and start both services
docker compose up --build
```

- **Frontend Web App**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8001](http://localhost:8001)
- **Swagger docs**: [http://localhost:8001/docs](http://localhost:8001/docs)

See the **Docker** section below for full details.

### Option 2: Running Locally (Manual Setup)

To run the application manually, you must run both the backend and frontend in separate terminal processes.

#### Step 1: Run the Backend API

##### Method A: Using uv (Recommended)
[uv](https://docs.astral.sh/uv/) is a fast Python package manager. It handles virtual environments and dependency resolution automatically.

```bash
# Install uv (if not installed)
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv automatically)
uv sync

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start the backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Run tests
uv run pytest tests/ -v
```

##### Method B: Using pip
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Run tests
pytest tests/ -v
```

#### Step 2: Run the Frontend (Next.js)

```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Next.js dev server
npm run dev
```
The frontend is served at [http://localhost:3000](http://localhost:3000) and automatically proxies API requests to [http://127.0.0.1:8001](http://127.0.0.1:8001).

#### Step 3: Run the Legacy Streamlit UI (Optional)
If you specifically want to run the older, deprecated Streamlit interface instead of the modern React web app:

```bash
# Using uv:
uv run streamlit run streamlit_app/app.py

# Using pip:
streamlit run streamlit_app/app.py
```
It will be available at [http://localhost:8501](http://localhost:8501).

---

## Configuration Reference

All configuration is via environment variables (or `.env` file).

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./mock.db` | Database connection string |
| `LLM_PROVIDER` | `gemini` | Which LLM to use |
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `QUERY_LOG_FILE` | `query_logs.json` | Path for query audit logs |
| `WEEK_DEFINITION` | `calendar` | `calendar` (Mon-Sun) or `rolling7` |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max requests per session per minute |
| `QUERY_TIMEOUT_SECONDS` | `10` | DB query timeout (PostgreSQL only) |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL for Streamlit |

---

## Connecting to Real PostgreSQL

1. Set up a PostgreSQL database with your college schema.

2. Create a read-only database role:
   ```sql
   CREATE ROLE chatbot_reader WITH LOGIN PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE college_db TO chatbot_reader;
   GRANT USAGE ON SCHEMA public TO chatbot_reader;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_reader;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_reader;
   ```

3. Update `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://chatbot_reader:secure_password@localhost:5432/college_db
   ```

4. Install the PostgreSQL async driver:
   ```bash
   pip install asyncpg
   ```

5. Update `app/schema/annotations.yaml` to match your real table names and add domain-specific notes.

6. Restart the backend. The schema introspector will auto-detect tables from `information_schema`.

---

## Swapping LLM Providers

The system is designed for easy LLM swapping. The architecture uses an abstract base class pattern:

### Current Provider: Gemini

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

### Adding a New Provider (e.g., OpenAI)

1. Create `app/llm/openai_provider.py`:

```python
from app.llm.base import BaseLLMProvider, AmbiguityResult

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        # Initialize OpenAI client
        ...

    async def classify_domain(self, question: str) -> str:
        # Use the same prompt templates
        ...

    async def generate_sql(self, question: str, schema_context: str) -> str:
        ...

    async def generate_response(self, question, sql, results, error=None):
        ...

    async def assess_ambiguity(self, question, schema_context):
        ...
```

2. Register in `app/llm/factory.py`:

```python
elif provider_name == "openai":
    from app.llm.openai_provider import OpenAIProvider
    return OpenAIProvider()
```

3. Set env vars:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

The prompt templates in `app/llm/prompts/templates.py` are provider-agnostic and can be reused across any LLM.

---

## Week Definition Configuration

The `WEEK_DEFINITION` env var controls how "last week" and "this week" are interpreted for trend queries:

- **`calendar`** (default): Weeks run Monday through Sunday. "Last week" is the previous Mon-Sun period.
- **`rolling7`**: "Last week" means the 7 days before today. "This week" is the most recent 7 days.

This affects the `TREND_SQL_GENERATION_PROMPT` which includes date boundaries when generating comparison queries.

---

## Security Model

### Defense in Depth (3 layers):

1. **Database Role** (when using PostgreSQL): The connection uses a role with only SELECT privileges. Even if SQL injection somehow occurs, the DB user cannot write.

2. **Application-Level SQL Validator**: Uses `sqlparse` to verify:
   - Single statement only (no `;`-separated multi-statements)
   - Statement type is SELECT (or WITH...SELECT for CTEs)
   - No forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE
   - No dangerous patterns even in comments
   - Query length limit (2000 chars)

3. **Query Timeout**: PostgreSQL connections set `statement_timeout` to prevent long-running queries from consuming resources.

### Additional Protections:

- Rate limiting: 10 requests per minute per session
- Input length validation: Questions capped at 500 characters
- Global exception handler: Internal errors never exposed to users
- LLM retry with backoff: Handles transient API failures gracefully

---

## API Endpoints

### `GET /health`
Health check. Returns environment, provider, and database type.

### `POST /api/chat`
Main chat endpoint.

**Request:**
```json
{
  "question": "How many students are in Center Delhi?",
  "conversation_id": "optional-uuid-for-follow-ups"
}
```

**Response:**
```json
{
  "answer": "There are 16 students in Center Delhi.",
  "sql": "SELECT COUNT(*) as count FROM Student s JOIN Center c ON s.center_id = c.id WHERE c.name = 'Center Delhi'",
  "is_clarification": false,
  "conversation_id": "uuid-here",
  "domain": "students",
  "row_count": 1
}
```

### `GET /api/logs?limit=50&offset=0`
Query audit log viewer with pagination. Returns logs in reverse chronological order.

---

## Key Design Decisions

1. **Domain Classification First**: Narrows the schema context to only relevant tables, reducing token usage and improving SQL accuracy.

2. **Ambiguity Detection**: Prevents bad SQL from vague questions. The bot asks for clarification instead of guessing.

3. **Trend-Specific Prompting**: Comparison queries (week-over-week, period-over-period) use a specialized prompt with CTE examples.

4. **Fallback Formatting**: If the LLM fails during response generation, the formatter has a rule-based fallback that still produces readable output.

5. **Conversation State**: In-memory (not persistent) for v1. Enables clarification follow-ups. Conversations expire after 10 minutes.

6. **JSON-Lines Logging**: Simple, append-only, parseable. Easy to ship to any log aggregator later.

---

## Docker

### Overview

The project ships with Dockerfiles for the backend, Next.js frontend, and legacy Streamlit interface, and a `docker-compose.yml` that orchestrates them:

```
┌─────────────────────────────────────────────────────────────┐
│                      docker compose up                      │
│                                                             │
│  ┌─────────────────────┐          ┌──────────────────────┐  │
│  │  backend             │          │  frontend            │  │
│  │  (Dockerfile)        │          │  (Dockerfile.front)  │  │
│  │                      │          │                      │  │
│  │  FastAPI + uv        │◄─────────│  Next.js             │  │
│  │  Port 8001           │ (Proxy)  │  Port 3000           │  │
│  └──────────┬──────────┘          └──────────────────────┘  │
│             │                                               │
│             ▼                                               │
│       SQLite (mock.db)                                      │
│       inside container                                      │
└─────────────────────────────────────────────────────────────┘
```

### Files Explained

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the **backend** image (FastAPI + Python dependencies) |
| `Dockerfile.frontend` | Builds the **Next.js frontend** image (Node/React application) |
| `Dockerfile.streamlit` | Builds the legacy **Streamlit UI** image (deprecated) |
| `docker-compose.yml` | Orchestrates backend, frontend, and legacy services, sets up the virtual network |
| `.dockerignore` | Excludes `.env`, `.git`, `tests`, `node_modules`, and Python cache directories |

### How the Docker Build Works

- **Backend Build**:
  1. **Base image**: `python:3.11-slim` (minimal environment)
  2. **Install uv**: Copies binary from `ghcr.io/astral-sh/uv` to optimize dependency caching
  3. **Dependency sync**: Copies `pyproject.toml` + `uv.lock` and runs `uv sync --frozen --no-dev`
  4. **Code copy**: Adds the app package and runs under a non-root `appuser` for security
- **Frontend Build**:
  1. **Base image**: `node:20-alpine`
  2. **Build stage**: Runs `npm install` and `npm run build` to build Next.js static and standalone bundle assets
  3. **Runner stage**: Copies standalone `server.js` and statically built pages into a production-ready container running under a non-root user

This setup ensures that builds are fully cached and very fast unless dependencies (`pyproject.toml` or `package.json`) change.

### Commands

```bash
# Build and start all services (Backend + Next.js Frontend)
docker compose up --build

# Start in background (detached mode)
docker compose up --build -d

# View logs for all running services
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Stop and tear down containers
docker compose down

# Remove containers, networks, and volumes
docker compose down -v
```

### Environment Variables in Docker

The `docker-compose.yml` automatically imports variables defined in your `.env` file via `env_file: .env`. Ensure you:

1. Copy `.env.example` to `.env`
2. Set your `GEMINI_API_KEY`
3. Run `docker compose up --build`

The frontend container sets the environment variable `NEXT_PUBLIC_API_URL=http://backend:8001`. Next.js uses this internal DNS address to resolve API requests securely through the shared Docker network.

### Health Checks

The backend service defines a health check:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
  interval: 10s
  timeout: 5s
  retries: 3
```

The `frontend` container depends on this health check being successful before it boots up (`depends_on` with `condition: service_healthy`), ensuring no API requests fail on launch.

### Using Real PostgreSQL with Docker

To connect to a PostgreSQL database from inside Docker:

```yaml
# In docker-compose.yml, change the backend environment:
environment:
  - DATABASE_URL=postgresql+asyncpg://user:pass@host.docker.internal:5432/college_db
```

`host.docker.internal` allows the container to contact a PostgreSQL instance running on your host machine. Alternatively, you can add a local PostgreSQL service directly in `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: college_db
      POSTGRES_USER: chatbot_reader
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    # ... existing config ...
    environment:
      - DATABASE_URL=postgresql+asyncpg://chatbot_reader:secure_password@db:5432/college_db
    depends_on:
      - db

volumes:
  pgdata:
```

### Building Individual Images

You can build and run individual images outside of Docker Compose:

```bash
# Build backend
docker build -t college-chatbot-backend .

# Build Next.js frontend
docker build -t college-chatbot-frontend -f Dockerfile.frontend .

# Run backend standalone
docker run -p 8001:8001 --env-file .env college-chatbot-backend

# Run frontend standalone (points proxy to host backend)
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://host.docker.internal:8001 college-chatbot-frontend
```

### Image Sizes

The images are optimized for production:
- Using `python:3.11-slim` and `node:20-alpine` base images
- `.dockerignore` blocks copying of large test caches, local environments, and `node_modules`
- Next.js build uses the `standalone` output target to package only the files needed for production

Expected sizes:
- Backend image: ~350MB
- Frontend image: ~150MB

---

## uv Package Manager

### Why uv?

- 10-100x faster than pip for installs
- Automatic virtual environment management
- Deterministic builds via `uv.lock`
- No need to manually create/activate venvs
- Compatible with `pyproject.toml` standard

### Key Commands

```bash
# Install all dependencies (creates .venv/)
uv sync

# Install with dev dependencies (for testing)
uv sync --dev

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Run a command in the project environment
uv run python -c "print('hello')"
uv run uvicorn app.main:app --reload
uv run pytest tests/ -v

# Update lock file after changing pyproject.toml
uv lock

# Show dependency tree
uv tree
```

### How It Works with Docker

The Dockerfiles use uv inside the container:
1. `uv sync --frozen` installs exactly what's in `uv.lock` (no resolution needed)
2. `uv run` runs commands using the installed environment
3. `--no-dev` excludes test dependencies from production images

### Fallback to pip

If you prefer pip, `requirements.txt` is still maintained. Both work:

```bash
# pip way
pip install -r requirements.txt
uvicorn app.main:app --reload

# uv way
uv sync
uv run uvicorn app.main:app --reload
```
