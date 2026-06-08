# Praxis — AI-Powered Career Management Platform

Praxis is an AI-powered career management platform built for **Codesprint 2026** by Poridhi.io. It helps job seekers upload their CV, discover matched jobs, track applications, get AI coaching, and generate career roadmaps — all in one place.

---

## Features

| Feature | Description |
|---|---|
| **Smart CV Parsing** | Upload PDF, DOCX, or images. Extracts skills, experience, education and generates 768-dim semantic embeddings via Jina AI. |
| **AI Job Hunter** | Personalized job suggestions from a semantic vector pool scored by skill overlap + cosine similarity. Live JSearch scraping. |
| **Application Tracker** | Kanban board (Saved → Applied → Interviewing → Offer / Rejected). Save jobs from suggestions with one click. |
| **AI Career Coach Chat** | Agentic chat with tool use — searches jobs, reads your applications, generates roadmaps, drafts cover letters. |
| **Cover Letter Drafter** | Tailored cover letters via Groq LLM. Tone control. Persistent drafts. |
| **Roadmap & Goals** | Auto-generated career roadmaps from CV gap analysis. Milestone tracking. |
| **Real-Time Notifications** | WebSocket push alerts for every significant event (CV processed, jobs found, session summarised). |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+ |
| Database | PostgreSQL + pgvector (Supabase hosted) |
| ORM | SQLAlchemy |
| Cache / Queue | Redis (Upstash TLS) |
| Background Jobs | ARQ worker |
| Auth | Supabase Auth (JWT) |
| File Storage | Supabase Storage |
| LLM | Groq — llama-3.3-70b-versatile |
| Embeddings | Jina AI — jina-embeddings-v2-base-en (768-dim) |
| Job Data | JSearch API (RapidAPI) |
| Frontend | React 18 + Vite 5 |

---

## Prerequisites

### macOS

- **Python 3.11+** — `brew install python@3.11` or via [python.org](https://python.org)
- **Node.js 18+** — `brew install node` or via [nodejs.org](https://nodejs.org)
- **Git** — `brew install git`

### Windows

- **Python 3.11+** — Download installer from [python.org](https://python.org). During install, check **"Add Python to PATH"**.
- **Node.js 18+** — Download LTS installer from [nodejs.org](https://nodejs.org).
- **Git** — Download from [git-scm.com](https://git-scm.com). Use **Git Bash** or PowerShell for all commands below.

---

## Backend Setup

### macOS

```bash
# 1. Go to the backend directory
cd backend

# 2. Create a virtual environment
python3 -m venv .venv

# 3. Activate it
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Windows

```powershell
# 1. Go to the backend directory
cd backend

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it  (PowerShell)
.venv\Scripts\Activate.ps1

# or in Command Prompt:
# .venv\Scripts\activate.bat

# 4. Install dependencies
pip install -r requirements.txt
```

### Configure Backend Environment Variables

Create a file named `.env` inside the `backend/` directory:

```env
# ── LLM (Groq) ──────────────────────────────────────────
LLM_API_KEY=your_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

LLM_FALLBACK_API_KEY=your_groq_api_key
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

# ── Chatbot (separate Groq key recommended) ──────────────
CHATBOT_API_KEY=your_groq_api_key
CHATBOT_BASE_URL=https://api.groq.com/openai/v1
CHATBOT_LLM_MODEL=llama-3.3-70b-versatile

CHATBOT_FALLBACK_API_KEY=your_groq_api_key
CHATBOT_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
CHATBOT_FALLBACK_MODEL=llama-3.3-70b-versatile

# ── Embeddings (Jina AI) ─────────────────────────────────
EMBEDDING_API_KEY=your_jina_api_key
EMBEDDING_BASE_URL=https://api.jina.ai/v1
EMBEDDING_MODEL=jina-embeddings-v2-base-en
EMBEDDING_DIMENSIONS=768

EMBEDDING_FALLBACK_API_KEY=your_jina_api_key
EMBEDDING_FALLBACK_BASE_URL=https://api.jina.ai/v1
EMBEDDING_FALLBACK_MODEL=jina-embeddings-v2-base-en

# ── Job Search (JSearch / RapidAPI) ──────────────────────
JSEARCH_API_KEYS=key1,key2,key3
JSEARCH_API_HOST=jsearch.p.rapidapi.com

# ── Supabase ─────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=cvs

# ── Database (Supabase PostgreSQL) ───────────────────────
DATABASE_URL=postgresql+psycopg2://postgres:password@db.your-project.supabase.co:5432/postgres

# ── Redis (Upstash) ──────────────────────────────────────
REDIS_URL=rediss://default:password@your-upstash-endpoint:6380
```

### Start the API Server

```bash
# macOS / Windows (from backend/ with venv active)
uvicorn main:app --reload
```

API runs at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

### Start the Background Worker

Open a **second terminal**, activate the venv again, then:

```bash
# macOS / Windows
arq app.core.worker.WorkerSettings
```

> The worker handles scheduled job scraping, embedding, and cache cleanup. The API works without it but job suggestions won't refresh automatically.

### Run Backend Tests

```bash
# macOS / Windows (from backend/ with venv active)
python -m pytest tests/ -v
```

---

## Frontend Setup

### macOS

```bash
# 1. Go to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the dev server
npm run dev
```

### Windows

```powershell
# 1. Go to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the dev server
npm run dev
```

### Configure Frontend Environment Variables

Create a file named `.env` inside the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Frontend runs at `http://localhost:5173`

---

## Running Order

Start services in this order:

1. **Backend API** — `uvicorn main:app --reload`
2. **ARQ Worker** — `arq app.core.worker.WorkerSettings` (separate terminal)
3. **Frontend** — `npm run dev` (separate terminal inside `frontend/`)

---

## Project Structure

```
praxis/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py               # Router registration
│   │   ├── core/                # Config, session, auth, worker
│   │   └── modules/             # auth, cv, jobs, application,
│   │       ...                  # chat, roadmap, goals,
│   │                            # notifications, cover_letter
│   └── tests/
│       └── test_core.py         # 5 guaranteed-pass unit tests
└── frontend/
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── api.js               # All API calls
        ├── AuthContext.jsx      # Auth state (useAuth hook)
        └── components/          # Jobs, Applications, Chat, Goals…
```

---

## Architecture

See [architecture.svg](architecture.svg) for a visual system diagram and [architecture.md](architecture.md) for detailed flow diagrams covering auth, CV pipeline, job suggestion pool, chat tool orchestration, and the notification system.

---

*Praxis · Codesprint 2026 · Poridhi.io*
