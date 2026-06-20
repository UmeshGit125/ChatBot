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
├── requirements.txt                 # Python dependencies
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

- Python 3.11+
- A Google Gemini API key (get one at https://aistudio.google.com/apikey)

### Setup

```bash
# Clone and enter the project
cd college-chatbot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### Start the Backend

```bash
# From the college-chatbot/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000. Check http://localhost:8000/docs for the Swagger UI.

### Start the Streamlit UI

In a separate terminal:

```bash
# From the college-chatbot/ directory
streamlit run streamlit_app/app.py
```

The chat UI will open at http://localhost:8501.

### Run Tests

```bash
pytest tests/ -v
```

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
