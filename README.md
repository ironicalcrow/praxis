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

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure Environment Variables. Create a `.env` file in the `backend` directory with the following keys:
-SUPABASE_URL=
-SUPABASE_ANON_KEY=
-SUPABASE_SERVICE_ROLE_KEY=
-SUPABASE_STORAGE_BUCKET=cvs

-DATABASE_URL=

-REDIS_URL=

-LLM_FALLBACK_API_KEY=
-LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
-LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

-CHATBOT_FALLBACK_API_KEY=
-CHATBOT_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
-CHATBOT_FALLBACK_MODEL=llama-3.3-70b-versatile

-EMBEDDING_FALLBACK_API_KEY=
-EMBEDDING_FALLBACK_BASE_URL=https://api.jina.ai/v1
-EMBEDDING_FALLBACK_MODEL=jina-embeddings-v2-base-en

5. Run the database migrations (if any) or ensure the DB is setup. The backend automatically creates tables on startup if `Base.metadata.create_all` is enabled.

6. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```

7. Run the background worker for cron tasks and background jobs in a separate terminal:
   ```bash
   arq app.core.worker.WorkerSettings
   ```

## Testing

To run the evaluation suite:
```bash
pytest
```
