# Praxis - AI-Powered Career Management Platform

Praxis is an AI-powered career management platform built for the Codesprint 2026 hackathon. The backend is a production-grade FastAPI service backed by PostgreSQL + pgvector, Redis, ARQ background workers, Supabase, Groq LLM, and Jina AI embeddings.

## Features

- **Smart CV Parsing:** Upload PDFs, DOCX, or images. Extracts structured data (skills, experience, etc.) and generates semantic embeddings using Jina AI.
- **AI Job Hunter:** Real-time job search via JSearch API with a personalized suggestion pool. Calculates a fit score based on your CV and job requirements.
- **Cover Letter Drafter:** Generate tailored cover letters using Groq LLM. Control tone and store drafts.
- **Application Tracker:** Kanban board view to track your applications from 'Saved' to 'Offer'.
- **AI Career Coach Chat:** Job-scoped chat with agentic tool use. Get resume advice, roadmaps, and more.
- **Roadmap & Goals:** Generate career roadmaps automatically from chat or job gaps. Track your goals.
- **Real-Time Notifications:** WebSocket based real-time alerts for all critical events.

## Tech Stack
- **Backend Framework:** FastAPI
- **Database:** PostgreSQL (with `pgvector`)
- **Caching & Pub/Sub:** Redis
- **Background Tasks:** ARQ
- **Auth & Storage:** Supabase
- **AI Models:** Groq (Llama-3), Jina AI
- **Job Data:** JSearch API

## Setup Instructions

### 1. Backend Setup

Navigate to the `backend` directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

For macOS/Linux:

```bash
source .venv/bin/activate
```

For Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure Backend Environment Variables

Create a `.env` file inside the `backend` directory:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=cvs

DATABASE_URL=

REDIS_URL=

LLM_FALLBACK_API_KEY=
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

CHATBOT_FALLBACK_API_KEY=
CHATBOT_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
CHATBOT_FALLBACK_MODEL=llama-3.3-70b-versatile

EMBEDDING_FALLBACK_API_KEY=
EMBEDDING_FALLBACK_BASE_URL=https://api.jina.ai/v1
EMBEDDING_FALLBACK_MODEL=jina-embeddings-v2-base-en
```

### 3. Database Setup

Run database migrations if migrations are configured.

If migrations are not used, ensure the database is running and the backend can connect to it. The backend automatically creates tables on startup if `Base.metadata.create_all` is enabled.

### 4. Run the Backend Server

Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

The backend will run at:

```text
http://localhost:8000
```

Swagger API documentation will be available at:

```text
http://localhost:8000/docs
```

### 5. Run the Background Worker

In a separate terminal, go to the `backend` directory and activate the virtual environment again.

Then run:

```bash
arq app.core.worker.WorkerSettings
```

---

## Frontend Setup

### 1. Navigate to the Frontend Directory

From the project root:

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Frontend Environment Variables

Create a `.env` file inside the `frontend` directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 4. Run the React Development Server

```bash
npm run dev
```

The frontend will usually run at:

```text
http://localhost:5173
```

Make sure the backend server is running at:

```text
http://localhost:8000
```

---

## Testing

To run the evaluation suite:

```bash
pytest
```
