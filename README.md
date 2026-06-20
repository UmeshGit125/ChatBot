# College Data Chatbot

A natural language chatbot that lets you query a college operations database using plain English, Hindi, or Hinglish. No SQL knowledge needed — just ask questions and get answers.

Built with **FastAPI**, **Google Gemini**, **LangChain**, **SQLAlchemy**, and **Streamlit**.

---

## What It Does

- Translates natural language questions into SQL queries
- Supports English, Hindi, and Hinglish input
- Returns smartly formatted responses (tables, summaries, natural language)
- Handles follow-up questions and clarifications
- Strict read-only guardrails — only SELECT queries ever reach the database
- Covers 8 domains: Attendance, Academics, Coding, Clubs, Placements, Students, Projects, Certifications

## Example Queries

| Question | What it does |
|----------|-------------|
| "How many students are in Center Delhi?" | Counts active students |
| "Top 5 students in Math Mid-Term exam" | Ranks by marks |
| "Students whose attendance rose by 30% from week 1 to week 2" | Week-over-week comparison |
| "Who got placed with salary > 10 LPA?" | Filters placements |
| "Rohan ne kitne problems solve kiye?" | Hinglish query support |

---

## Architecture

```
User Question (EN/HI/Hinglish)
        │
        ▼
┌───────────────────────────┐
│  FastAPI Backend           │
│  ├─ Domain Classification  │
│  ├─ Schema Context Builder │
│  ├─ Ambiguity Detection    │
│  ├─ SQL Generation (Gemini)│
│  ├─ SQL Validation         │
│  ├─ Query Execution        │
│  └─ Response Formatting    │
└───────────────┬───────────┘
                │
                ▼
┌───────────────────────────┐
│  Streamlit Chat UI         │
│  Chat interface + SQL view │
└───────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Uvicorn |
| LLM | Google Gemini 2.5 Flash (swappable) |
| Database | PostgreSQL (prod) / SQLite (dev) |
| ORM | SQLAlchemy (async) |
| SQL Validation | sqlparse |
| Schema Metadata | YAML + DB introspection |
| Frontend | Streamlit |
| Config | pydantic-settings |
| Testing | pytest (80 tests) |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/college-chatbot.git
cd college-chatbot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

API available at http://localhost:8000 | Swagger docs at http://localhost:8000/docs

### Run the Chat UI

```bash
streamlit run streamlit_app/app.py
```

Opens at http://localhost:8501

### Run Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
college-chatbot/
├── app/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── api/
│   │   ├── chat.py             # POST /api/chat
│   │   └── logs.py             # GET /api/logs
│   ├── core/
│   │   ├── config.py           # Environment configuration
│   │   ├── pipeline.py         # NL → SQL orchestration
│   │   ├── models.py           # Request/Response schemas
│   │   ├── conversation.py     # Conversation state management
│   │   ├── logger.py           # Query audit logging
│   │   ├── rate_limiter.py     # Rate limiting
│   │   └── week_utils.py       # Week boundary calculations
│   ├── llm/
│   │   ├── base.py             # Abstract LLM interface
│   │   ├── gemini_provider.py  # Gemini implementation
│   │   ├── factory.py          # Provider factory
│   │   └── prompts/            # Prompt templates
│   ├── db/
│   │   ├── connection.py       # DB connection + query executor
│   │   ├── mock_schema.sql     # Mock DB schema (16 tables)
│   │   └── seed_data.sql       # Sample data
│   ├── schema/
│   │   ├── introspector.py     # Live schema reader
│   │   ├── annotations.yaml    # Curated table descriptions
│   │   └── context_builder.py  # Schema → LLM context
│   ├── guardrails/
│   │   └── sql_validator.py    # SELECT-only enforcement
│   └── formatter/
│       └── response_formatter.py
├── streamlit_app/
│   └── app.py                  # Chat UI
├── tests/                      # 80 tests across all modules
├── docs/
│   └── GUIDE.md                # Detailed developer guide
├── .env.example
└── requirements.txt
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `DATABASE_URL` | `sqlite+aiosqlite:///./mock.db` | DB connection string |
| `LLM_PROVIDER` | `gemini` | LLM provider (`gemini`) |
| `WEEK_DEFINITION` | `calendar` | `calendar` (Mon-Sun) or `rolling7` |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max requests per session |

---

## Connecting to Real PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/college_db
```

Create a read-only DB role for safety:
```sql
CREATE ROLE chatbot_reader WITH LOGIN PASSWORD 'password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_reader;
```

---

## Swapping LLM Providers

The system uses an abstract `BaseLLMProvider` class. To add a new provider:

1. Create a new class implementing `BaseLLMProvider` in `app/llm/`
2. Register it in `app/llm/factory.py`
3. Set `LLM_PROVIDER=your_provider` in `.env`

See [docs/GUIDE.md](docs/GUIDE.md) for detailed instructions.

---

## Security

- **SQL Validator**: Only SELECT statements allowed (no writes, no DDL)
- **Read-only DB role**: Defense-in-depth at database level
- **Rate limiting**: 10 requests/minute per session
- **Input validation**: 500 char max question length
- **Query timeout**: Configurable statement timeout
- **Error handling**: Internal errors never exposed to users

---

## API Endpoints

### `POST /api/chat`
```json
// Request
{ "question": "How many students?", "conversation_id": "optional-uuid" }

// Response
{ "answer": "There are 25 students.", "sql": "SELECT COUNT(*)...", "domain": "students" }
```

### `GET /api/logs?limit=50`
Returns query audit logs for debugging and accuracy review.

### `GET /health`
Health check with environment info.

---

## License

MIT
