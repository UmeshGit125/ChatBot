# College Data Chatbot

A natural language chatbot that lets you query a college operations database using plain English, Hindi, or Hinglish. No SQL knowledge needed — just ask questions and get answers.

Built with **FastAPI**, **Google Gemini**, **SQLAlchemy**, and **Streamlit**. Managed with **uv**. Containerized with **Docker**.

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
| Package Manager | uv |
| Containerization | Docker + Docker Compose |
| Testing | pytest (80 tests) |

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+ and npm** (required to run the Next.js frontend locally)
- A **[Google Gemini API key](https://aistudio.google.com/apikey)**

---

### Option 1: Running with Docker (Recommended & Easiest)

No Python or Node.js installation is required on your machine. Docker handles the entire stack: the FastAPI backend, the Next.js frontend, and the database automatically.

1. Clone and navigate to the project directory:
   ```bash
   git clone https://github.com/UmeshGit125/ChatBot.git
   cd ChatBot
   ```

2. Configure the environment variables:
   ```bash
   cp .env.example .env
   # Open .env and add your GEMINI_API_KEY
   ```

3. Start all services:
   ```bash
   docker compose up --build
   ```

Once started:
- **Frontend Web App**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the containers:
```bash
docker compose down
```

> [!NOTE]
> If you wish to run the legacy/deprecated Streamlit interface, you can start it with the legacy profile:
> ```bash
> docker compose --profile legacy up --build
> ```
> The Streamlit interface will be available at [http://localhost:8501](http://localhost:8501).

---

### Option 2: Running Locally (Without Docker)

To run without Docker, you will need to start both the Backend API and the Next.js Frontend in separate terminal windows.

#### Step 1: Run the Backend API

You can install dependencies and run the backend using either **uv** (recommended) or **pip**.

##### Method A: Using uv (Fastest)
[uv](https://docs.astral.sh/uv/) is an extremely fast Python package manager.

```bash
# Install uv (if you don't have it)
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup dependencies (automatically creates virtual environment)
uv sync

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

##### Method B: Using pip
```bash
# Setup virtual environment (optional but recommended)
python -m venv .venv
# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start backend server
uvicorn app.main:app --reload --port 8000
```

The Backend API is now running at [http://localhost:8000](http://localhost:8000).

#### Step 2: Run the Frontend (Next.js)

Navigate to the `frontend` folder to install dependencies and run the dev server:

```bash
# Open a new terminal window and go to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Next.js development server
npm run dev
```

The frontend web app is now running at [http://localhost:3000](http://localhost:3000). It is pre-configured to proxy API calls to the backend on port 8000.

#### Step 3: Run the Legacy Streamlit UI (Optional)

If you specifically want to run the older, deprecated Streamlit interface instead of the modern React web app:

```bash
# Using uv:
uv run streamlit run streamlit_app/app.py

# Or using pip (with active virtual environment):
streamlit run streamlit_app/app.py
```
It will be available at [http://localhost:8501](http://localhost:8501).

#### Running Tests

Verify the backend works correctly:
```bash
# Using uv:
uv run pytest tests/ -v

# Or using pip:
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
├── Dockerfile                  # Backend container
├── Dockerfile.streamlit        # Streamlit UI container
├── docker-compose.yml          # Multi-container orchestration
├── pyproject.toml              # Project config + dependencies (uv)
├── uv.lock                     # Locked dependency versions
├── requirements.txt            # pip fallback
└── .env.example                # Environment template
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
