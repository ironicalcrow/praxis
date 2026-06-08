# 🌌 Praxis — AI-Powered Career Management Platform

**Praxis** is an intelligent, production-grade career management platform built for the **Codesprint 2026 Hackathon**. It acts as a comprehensive command center for job seekers, combining advanced LLMs, semantic vector search, real-time event streams, and background scraping workers into a seamless React-FastAPI application.

---

## 🏗️ System Architecture & Data Flow

Praxis is designed to be highly decoupled, event-driven, and fault-tolerant. Below is the end-to-end architecture showing how the client, backend, database, queue worker, and external services interact:

```mermaid
graph TD
    subgraph Client [Client Tier]
        FE[React / Vite Frontend]
        WS[WebSocket Notification Listener]
    end

    subgraph Backend [FastAPI Application Server]
        API[FastAPI Endpoints]
        WSM[WebSocket Manager]
        FS[CV Parser & Text Extractor]
        FIT[Fit Scorer]
    end

    subgraph Background [Background Task Worker]
        ARQ[ARQ Task Worker]
    end

    subgraph Storage [Database & Cache Tier]
        DB[(PostgreSQL + pgvector)]
        REDIS[(Upstash Redis Cache & Pub/Sub)]
        SUB_STOR[(Supabase Storage Buckets)]
    end

    subgraph External [AI Models & External APIs]
        GROQ[Groq Llama-3.3 LLM]
        JINA[Jina AI Embedding API]
        JSEARCH[JSearch RapidAPI]
        SUB_AUTH[Supabase Auth JWT]
    end

    %% Client Interactions
    FE -->|HTTP API Requests| API
    FE -->|Real-time Connection| WSM
    
    %% API Interactions
    API -->|Decode & Validate JWT| SUB_AUTH
    API -->|Store & Query Entities| DB
    API -->|Read/Write Suggestion Cache| REDIS
    API -->|Persist original CV documents| SUB_STOR
    API -->|Enqueue Heavy Scrapes| ARQ
    
    %% Worker Interactions
    ARQ -->|Poll Task Queue| REDIS
    ARQ -->|Scrape Jobs| JSEARCH
    ARQ -->|Fetch Vector Embeddings| JINA
    ARQ -->|Insert Scraped Jobs & Queries| DB
    
    %% Parsing & Scoring Logic
    FS -->|Extract Text| PyMuPDF / EasyOCR
    FS -->|Structured JSON Extraction| GROQ
    FIT -->|Compute Fit Score| DB
```

---

## ⭐ Key Features (The 7 Pillars of Praxis)

### 📄 1. Smart CV Parsing
- **Format Support:** Upload PDFs, DOCX, or images (PNG/JPG).
- **Extraction Pipeline:** Reads text using `PyMuPDF` (PDFs), `python-docx` (DOCX), or `EasyOCR` (Images). Groq's `llama-3.3-70b-versatile` LLM normalizes raw text into structured JSON (skills, experience, education, projects, certifications).
- **Semantic Mapping:** Generates 768-dimension embeddings via Jina AI and stores them in PostgreSQL using the `pgvector` extension.
- **Storage:** Persists original files securely in Supabase Storage (`cvs/` bucket).
- **History & Versioning:** Tracks all uploaded CVs; users can toggle and reactivate past CVs in one click, triggering auto-re-indexing and suggestions update.

### 🔍 2. AI Job Hunter
- **Scraping Engine:** Integrated with the JSearch API (RapidAPI) featuring a 3-key rotation mechanism to bypass rate limits.
- **Personalized Suggestion Pool:** Pre-computes 50 jobs tailored to the user. Uses a blended vector search: **70% CV embedding + 30% user preferences (work arrangements like remote/hybrid/full-time)**.
- **Windowed Pagination:** Delivers jobs in increments of 10. When the pool reaches 60% consumption, it pre-fetches fresh jobs in the background. When 100% consumed, it recycles the pool and auto-refreshes search queries.
- **Fit Scoring:** A composite score is calculated using **50% semantic vector match + 50% case-insensitive skill overlap**, generating detailed strengths, weaknesses, and match verdicts.

### ✍️ 3. Cover Letter Drafter
- **Tailored Generation:** Synthesizes the active CV and job description to draft a high-quality cover letter.
- **Tone Control:** Supports adjusting tones (`Professional`, `Enthusiastic`, `Concise`) and provides a full CRUD system to save, edit, and export drafts.

### 📋 4. Application Tracker
- **Kanban Board:** Visually track job application progress through phases: `Saved` ➔ `Applied` ➔ `Interviewing` ➔ `Offer` ➔ `Rejected`.
- **Status Audit History:** Maintains a transaction log of every status change (timestamp, old status, new status).
- **Notes System:** Add and update rich notes/feedback logs directly under each application.

### 💬 5. AI Career Coach Chat
- **Zero-Friction Context:** Grounded in a condensed version of the user's CV.
- **Memory Retention:** Tracks conversation sessions. Every 15 messages, sessions auto-rotate: the LLM creates a concise bulleted summary of key advice and skill gaps, which is passed as context to the next session.
- **Confirmation-First Agentic Tools:** Uses tool calls to interact with the database. "Read" tools run instantly, while "Write" tools (e.g., saving a job, creating roadmaps/goals, drafting letters) describe their plan and wait for the user to say "Yes" before executing.

### 🗺️ 6. Roadmaps & Goals
- **Tailored Roadmaps:** Automatically generates phased career roadmaps complete with milestones, duration, and resources, based on chat transcripts or CV-to-job skill gap analyses.
- **Goal Promotion:** Users can promote milestones directly into tracked goals.
- **Goal Tracking:** Set target dates and update statuses (`Not Started` ➔ `In Progress` ➔ `Completed` ➔ `Paused`).

### 🔔 7. Real-Time Notification Center
- **WebSocket Transport:** Live WebSocket stream for instant updates (e.g., CV parsed, cover letter ready, application updated, goal completed).
- **Redis Pub/Sub & Persistence:** Pushes events through Redis channels. Every notification is stored in PostgreSQL first to allow **offline catch-up**—when a user reconnects, unread notifications are delivered first.
- **Multi-Tab Support:** Handles multiple active tabs for a single user using a thread-safe connection manager.

---

## 🛠️ Tech Stack & Dependencies

### 🟢 Backend
- **Web Framework:** FastAPI (ASGI server)
- **Database ORM:** SQLAlchemy + PostgreSQL + `pgvector` (Hosted on Supabase)
- **Background Tasks:** ARQ (Async Redis Queue)
- **Real-Time Layer:** Redis (Pub/Sub) (Hosted on Upstash) + WebSockets
- **Document Parsers:** PyMuPDF, python-docx, EasyOCR (for image parsing)
- **AI Frameworks:** Groq LLM API, Jina AI Embeddings API

### 🔵 Frontend
- **Framework:** React 18 (with Hooks and Context API)
- **Build Tool:** Vite 5
- **Styling:** Custom Glassmorphic Vanilla CSS (configured for a dark premium interface)
- **Communication:** Native WebSocket + HTTP Fetch clients

---

## 🔑 Environment Variables Configuration

The backend connects to external database and caching environments. Ensure you have a `.env` file inside the `backend/` directory configured with the following parameters:

| Variable | Description | Provider |
| :--- | :--- | :--- |
| `LLM_BASE_URL` | Base endpoint for the primary LLM | Groq (`https://api.groq.com/openai/v1`) |
| `LLM_API_KEY` | API Key for LLM operations (CV parsing, etc.) | Groq / OpenRouter |
| `LLM_MODEL` | Model identifier to use | `llama-3.3-70b-versatile` |
| `CHATBOT_BASE_URL` | Base endpoint for the career coach LLM | Groq (`https://api.groq.com/openai/v1`) |
| `CHATBOT_API_KEY` | API Key for the chatbot assistant | Groq / OpenRouter |
| `CHATBOT_LLM_MODEL` | Model identifier for chatbot coaching | `llama-3.3-70b-versatile` |
| `EMBEDDING_BASE_URL` | Base endpoint for embedding generation | Jina AI (`https://api.jina.ai/v1`) |
| `EMBEDDING_API_KEY` | API Key for generating semantic vectors | Jina AI |
| `EMBEDDING_MODEL` | Embedding model to invoke | `jina-embeddings-v2-base-en` |
| `EMBEDDING_DIMENSIONS` | Dimensionality of vectors (stored in pgvector) | `768` |
| `JSEARCH_API_KEYS` | Comma-separated list of RapidAPI keys | JSearch (RapidAPI) |
| `JSEARCH_API_HOST` | Host header for JSearch API | `jsearch.p.rapidapi.com` |
| `JSEARCH_URL` | Live job search endpoint | `https://jsearch.p.rapidapi.com/search` |
| `JSEARCH_DETAIL_URL` | Job detail scraping endpoint | `https://jsearch.p.rapidapi.com/job-details` |
| `SUPABASE_URL` | Supabase Cloud instance URL | Supabase Auth + Storage |
| `SUPABASE_ANON_KEY` | Public client anon key for Auth | Supabase |
| `SUPABASE_SERVICE_ROLE_KEY`| Service key to bypass row levels for storage | Supabase |
| `SUPABASE_STORAGE_BUCKET` | Name of the bucket containing resume files | `cvs` |
| `DATABASE_URL` | PostgreSQL connection string | PostgreSQL (with `pgvector` enabled) |
| `REDIS_URL` | Redis connection URL (`redis://` or `rediss://` for TLS) | Redis / Upstash Redis |

---

## 🚀 Step-by-Step Startup Guide

### 1. Startup the Backend

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows (cmd/Powershell)
   python -m venv .venv
   .venv\Scripts\activate

   # On macOS/Linux
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the Database and flush Redis cache:
   The backend project includes a script to automatically flush Redis, drop previous schemas, and initialize the PostgreSQL tables based on SQLAlchemy models:
   ```bash
   python reset_db.py
   ```

5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```
   *The server runs locally at `http://localhost:8000`. Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).*

6. Run the ARQ background worker for background tasks and scraping:
   Open a **new terminal**, navigate to `backend/`, activate the virtual environment, and run:
   ```bash
   arq app.core.worker.WorkerSettings
   ```

---

### 2. Startup the Frontend

1. Navigate to the `frontend/` directory from the root:
   ```bash
   cd frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   *The React application will run locally at [http://localhost:3000](http://localhost:3000).*

---

## 🧪 Testing and Validation

### Run Automated Tests
To execute the backend test suites, run `pytest` from the `backend/` directory:
```bash
pytest
```

### Manual Verification Flows (Pitching to a Judge)
1. **Auth:** Register a new user at `http://localhost:3000` or log in.
2. **CV Processing:** Upload a CV in PDF/DOCX format. Check the WebSocket notification badge when the parser completes (`cv_parsed` event).
3. **Suggestions & Fit Scores:** Navigate to the Jobs page. The recommendation engine fetches jobs from the suggestion pool and displays a percentage match breakdown.
4. **Interactive Coaching:** Open the coach tab, type "What are my strongest skills?". The assistant will list items grounded in your CV. Ask "Create a roadmap for me"—observe the confirmation-first behavior before the roadmap gets created in the DB!
5. **Real-time Notifications:** In a separate window or tab, update an application status or complete a goal, and watch the visual notification slide in instantly via WebSockets.
