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
   - `DATABASE_URL`
   - `REDIS_URL`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GROQ_API_KEY`
   - `JINA_API_KEY`
   - `RAPIDAPI_KEY` (for JSearch)
   - `JWT_SECRET` (if applicable)

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
