# CareerPilot — Codesprint 2026 Implementation Status

CareerPilot is an AI-powered career management platform built for the Codesprint 2026 hackathon by Poridhi.io. The backend is a production-grade FastAPI service backed by PostgreSQL + pgvector, Redis (Upstash), ARQ background workers, Supabase Auth + Storage, Groq LLM, and Jina AI embeddings. The frontend is a React/Vite SPA. This document maps every hackathon requirement to its current state.

**Legend:** ✅ Done · ⚠️ Partial / needs improvement · ❌ Not built

---

## Pillar-by-Pillar Status

### Pillar 1 — Smart CV Parsing ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Upload PDF, DOCX, image (PNG/JPG) | ✅ | `POST /api/cv/upload-cv` — PyMuPDF, python-docx, EasyOCR |
| LLM-structured extraction (skills, experience, education, projects, certs) | ✅ | Groq llama-3.3-70b-versatile extracts normalized JSON |
| Vector embedding stored for semantic search | ✅ | Jina AI 768-dim, stored in `resumes.embedding` (pgvector) |
| Supabase Storage file persistence | ✅ | `cvs/{user_id}/{uuid}.ext` bucket |
| CV version history + re-activation | ✅ | `cv_uploads` table; `POST /api/cv/uploads/{id}/activate` re-parses & re-embeds |
| Notification on upload + activation | ✅ | `cv_parsed` / `cv_activated` pushed via WebSocket |
| Frontend CV upload UI | ✅ | `frontend/src/components/CV.jsx` — upload form, version history, activation |

**What could improve:** OCR quality on low-res images (EasyOCR CPU mode); no multi-language CV support.

---

### Pillar 2 — AI Job Hunter ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Live job search (real-time) | ✅ | JSearch API via `POST /api/jobs/live-search`; 24h cache, multi-page |
| Personalized suggestion pool (semantic) | ✅ | 50-job pool in Redis; pgvector cosine search; windowed 10 at a time |
| Fit score with explanations | ✅ | Skill overlap (50%) + semantic similarity (50%); verdict + matched/missing skills |
| Job detail view (full structured card) | ✅ | `GET /api/jobs/details/{job_id}` — title, company, salary, apply URLs, description |
| User preferences (remote/hybrid/full-time) | ✅ | Preference vector blended 30% with CV vector; `PUT /api/jobs/preferences` |
| Auto LLM-generated search queries from CV | ✅ | 5 queries generated on CV upload; `POST /api/jobs/queries/refresh` |
| Prefetch at 60% pool consumed, recycle at 100% | ✅ | ARQ background scrape triggered automatically |
| Recency filter (30-day cutoff) | ✅ | pgvector query filters `posted_at >= NOW() - 30d OR NULL` |
| Fallback if DB empty (live seed) | ✅ | JSearch live seed for first-time users |
| Frontend Jobs UI | ✅ | `frontend/src/components/Jobs.jsx` — suggestion pool, live search, fit score cards |

**What could improve:** No de-duplication across JSearch API key rotations. Salary data often missing (JSearch gap).

---

### Pillar 3 — Cover Letter Drafter ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Generate tailored cover letter (CV + job description → LLM) | ✅ | `POST /api/cover-letter/generate` — tone-controlled Groq generation |
| Store / edit / download drafts | ✅ | `GET/PATCH/DELETE /api/cover-letter/{id}` — full CRUD on saved drafts |
| Regenerate with tone control | ✅ | `tone` field: `professional`, `enthusiastic`, `concise` |
| Notification on generation | ✅ | `cover_letter_ready` pushed via WebSocket |
| Frontend Cover Letters UI | ✅ | `frontend/src/components/CoverLetters.jsx` — generate, view, edit drafts |

---

### Pillar 4 — Application Tracker ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Save a job to tracker | ✅ | `POST /api/application/applications/from-job` or `/manual` |
| Statuses: SAVED → APPLIED → INTERVIEWING → OFFER → REJECTED | ✅ | Full enum, status history logged |
| Kanban board view | ✅ | `GET /api/application/applications/kanban` — grouped by status |
| Notes per application | ✅ | `POST /api/application/applications/{id}/notes` |
| Archive / soft-delete | ✅ | `PATCH /api/application/applications/{id}/archive` |
| Status change history audit | ✅ | `application_status_history` table with old/new status + timestamp |
| Notifications on status change | ✅ | applied / interviewing / offer / rejected push WebSocket alerts |
| Frontend Applications UI | ✅ | `frontend/src/components/Applications.jsx` — kanban board, status changes, notes |

---

### Pillar 4b — Calendar / To-Do ❌

| Requirement | Status | Notes |
|-------------|--------|-------|
| Deadline calendar for applications | ❌ | Goals have `target_date` only; no calendar module |
| To-do task management | ❌ | Not implemented |
| Reminder notifications for deadlines | ❌ | No date-triggered notification scheduler |

**To build:**
1. `todos` table (user_id, title, due_date, linked_application_id, is_done, created_at)
2. `POST/GET/PATCH/DELETE /api/todos` — CRUD
3. APScheduler or ARQ CRON: daily scan for upcoming deadlines → push `deadline_reminder` notifications

---

### Pillar 5 — AI Career Coach Chat ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Zero-friction chat (no session/conversation ID management) | ✅ | `POST /api/chat/message` — backend silently manages all lifecycle |
| Job-scoped chat from job card | ✅ | `POST /api/chat/job/{job_id}/message` — fit score + job context pre-loaded |
| CV-grounded context (token-efficient) | ✅ | Compressed CV (~150 tokens): Name, YOE, top skills, roles — no raw text |
| Agentic tool use with confirmation-first rule | ✅ | Read tools execute immediately; write tools (roadmap, goals, cover letter, tracker) describe and ask before acting |
| Tool set — general chat | ✅ | `search_jobs`, `get_my_applications`, `get_my_goals`, `generate_roadmap`, `create_goals` |
| Tool set — job chat | ✅ | All general tools + `get_fit_score`, `save_to_tracker`, `draft_cover_letter` |
| Auto session rotation at 15 messages | ✅ | Background summarize → mark old session inactive → create new session |
| Chat history with pagination | ✅ | `GET /api/chat/history?before=<id>&limit=20` |
| Past session summary cards | ✅ | `GET /api/chat/sessions` — each session shows summary + date |
| Raw message pruning (keep last 2 sessions only) | ✅ | Weekly CRON + auto-prune on session rotation |
| Roadmap generation from chat | ✅ | `POST /api/roadmap/from-conversation` reads transcript → generates phases/milestones |
| Notification on session summarized | ✅ | `conversation_summarized` pushed via WebSocket |
| Roadmap nudge when skill gap detected in summary | ✅ | `coach_roadmap_nudge` notification fired after session rotation |
| Frontend Chat UI | ✅ | `frontend/src/components/Chat.jsx` — general + job-scoped chat, session history |
| Separate chatbot LLM caller | ✅ | `backend/app/core/chatbot_caller.py` — isolated from CV/job LLM calls |

**Token budget per call:** ~1,680 tokens (system prompt + compressed CV + job context + 1 session summary + 10 recent messages + tool schemas). Down from ~6,000 in previous design.

---

### Pillar 6 — Roadmap & Goals ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Generate roadmap from coaching conversation | ✅ | `POST /api/roadmap/from-conversation` — LLM reads transcript |
| Generate roadmap from job gap analysis | ✅ | `POST /api/roadmap/from-job` — LLM diffs user CV vs job description |
| Manual roadmap creation | ✅ | `POST /api/roadmap/manual` |
| Phases + milestones with durations and resources | ✅ | `roadmap_phases` → `roadmap_milestones` (description, resource_url, estimated_days) |
| Promote milestones → goals (user-selected) | ✅ | `POST /api/goals/from-roadmap/{roadmap_id}` |
| Goal status tracking (not_started → completed) | ✅ | not_started / in_progress / completed / paused |
| Goal target date | ✅ | `target_date` field on every goal |
| Notifications (roadmap generated, goals created, goal completed) | ✅ | `roadmap_generated`, `goals_created_from_roadmap`, `goal_completed` |
| Frontend Roadmaps UI | ✅ | `frontend/src/components/Roadmaps.jsx` — roadmap list, phases, milestones |
| Frontend Goals UI | ✅ | `frontend/src/components/Goals.jsx` — goal CRUD, status tracking |

---

### Progress Dashboard ❌

| Requirement | Status | Notes |
|-------------|--------|-------|
| Weekly job application count | ❌ | No stats endpoint |
| Goals completion percentage | ❌ | No aggregate query |
| Activity streak counter | ❌ | No streak tracking |
| Activity feed | ❌ | Notifications exist but no aggregated feed view |

**To build:**
- `GET /api/dashboard/stats` — aggregates across applications, goals, and roadmaps
  - `applications_this_week`, `applications_by_status`, `goals_total`, `goals_completed`, `streak_days`
- Streak: `user_activity` table (user_id, date) — log a row on any meaningful action; streak = consecutive days with activity

---

### AI Nudges / Proactive Alerts ⚠️

| Requirement | Status | Notes |
|-------------|--------|-------|
| Event-driven notifications (10 trigger types) | ✅ | cv_parsed, job_suggestions_ready, application_status_changed, goal_completed, etc. |
| WebSocket real-time delivery | ✅ | Redis pub/sub → WebSocket per connection |
| Offline catch-up (DB persistence) | ✅ | All notifications stored in `notifications` table; pushed on reconnect |
| Multi-tab support | ✅ | NotificationManager handles multiple WS per user_id |
| Frontend Notifications UI | ✅ | `frontend/src/components/Notifications.jsx` — live WS feed, mark read, history |
| Frontend WS in App.jsx | ✅ | `createNotificationWS()` in `api.js`; live toast-style feed in header |
| Scheduled / proactive nudges | ❌ | No cron-based "apply 3 jobs this week" or inactivity reminders |
| Deadline reminders | ❌ | No date-triggered notification scheduler |

**To build:**
- ARQ CRON job (daily @ 09:00): scan users with no application in 7 days → push `nudge_apply_jobs`
- ARQ CRON job (daily): scan goals with `target_date` in next 2 days → push `nudge_goal_deadline`

---

### Real-Time Notifications ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| WebSocket endpoint | ✅ | `WS /ws/notifications?token=<JWT>` |
| DB-persistent (no message loss) | ✅ | Every notification written to `notifications` table before Redis publish |
| REST endpoints (list, mark read, delete) | ✅ | `GET/PATCH/POST/DELETE /api/notifications/` |
| Mark all read | ✅ | `POST /api/notifications/mark-all-read` |
| Badge count (unread_only filter) | ✅ | `GET /api/notifications?unread_only=true` |

---

## Technical Infrastructure

| Component | Status | Details |
|-----------|--------|---------|
| FastAPI backend | ✅ | `backend/main.py` — 9 module routers |
| PostgreSQL (Supabase hosted) | ✅ | 20 tables, pgvector extension |
| pgvector semantic search | ✅ | 768-dim cosine distance on `jobs.embedding` + `resumes.embedding` |
| Redis pub/sub + caching (Upstash) | ✅ | Suggestion pool, notification delivery, ARQ queue |
| Supabase Auth (JWT) | ✅ | Bearer token on all endpoints; WS via query param |
| Supabase Storage | ✅ | CV file upload to `cvs/` bucket |
| ARQ background worker | ✅ | Job scraping CRON (6h), cleanup CRON (daily @ 01:00) |
| Groq LLM (llama-3.3-70b-versatile) | ✅ | CV parsing, query gen, fit scoring, roadmap, summarization |
| Groq LLM — chatbot (chatbot_caller.py) | ✅ | Separate caller for chat; isolated token budget |
| Jina AI embeddings (jina-embeddings-v2-base-en) | ✅ | 768-dim vectors for resumes, jobs, preferences |
| JSearch API (RapidAPI) | ✅ | Live job scraping, 3-key rotation |
| Providers abstraction layer | ✅ | `backend/app/providers/` — base.py + jsearch.py; ready for additional job providers |
| React/Vite frontend | ✅ | `frontend/` — 8 feature components, full API client, WS integration |
| Frontend production build | ✅ | `frontend/dist/` — compiled and ready to serve |
| Dockerfile / docker-compose | ❌ | No containerization |
| CI/CD | ❌ | No GitHub Actions |

---

## Hackathon Deliverables Checklist

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Functional AI-powered backend | ✅ | 40+ endpoints, production-grade |
| README.md with setup + env var guide | ✅ | 173-line guide — local setup, env vars, backend + frontend + worker |
| Architecture diagram | ❌ | No visual diagram committed |
| Frontend application (web or mobile) | ✅ | React/Vite SPA — all 8 pillars covered |
| System Design Document (bonus) | ❌ | `feature.md` covers architecture; not formatted as a formal SDD |
| Evaluation Suite — 5+ test cases (bonus) | ⚠️ | 5 smoke tests exist (root, health, docs, openapi, auth guard); no functional flow tests |

---

## Priority Build Queue

Ordered by hackathon scoring impact (highest first):

### 1. Architecture Diagram (Required deliverable, low effort)
- Draw.io or Excalidraw diagram showing: User → React → FastAPI → PostgreSQL/pgvector/Redis/Supabase/Groq/Jina/JSearch
- Export as PNG, commit to repo root

### 2. Evaluation Suite — Functional Tests (Bonus, medium effort)
Current: 5 smoke tests only. Need functional flow tests:
- CV upload + parse verification
- Job suggestion pool build + window advance
- Fit score computation
- Application status change + history
- Notification delivery (WebSocket or DB check)
- Cover letter generation

### 3. Progress Dashboard (High impact, medium effort)
- `GET /api/dashboard/stats` — application counts, goal completion %, this-week activity
- `user_activity` table for streak tracking
- Consider adding a `GET /api/dashboard/feed` combining notifications + status changes

### 4. Calendar / To-Do (Medium impact, medium effort)
- `todos` table + CRUD endpoints
- Deadline reminders via ARQ CRON

### 5. AI Nudges — Proactive Scheduling (Medium impact, medium effort)
- ARQ CRON: inactivity nudge (7-day no application)
- ARQ CRON: goal deadline reminder (2 days before target_date)
- ARQ CRON: weekly recap ("You applied to X jobs this week")

---

## File Structure

### Backend

```
backend/
├── main.py                          — FastAPI app + WebSocket route
├── app/
│   ├── api.py                       — Router aggregation
│   ├── models.py                    — All model imports (for Alembic)
│   ├── schemas.py                   — Shared Pydantic schemas
│   ├── core/
│   │   ├── config.py                — Settings (env vars via pydantic-settings)
│   │   ├── session.py               — SQLAlchemy SessionLocal + Base
│   │   ├── llm_caller.py            — Groq LLM + Jina embed_text() (CV/job/roadmap)
│   │   ├── chatbot_caller.py        — Groq LLM caller isolated for chat sessions
│   │   ├── supabase.py              — Supabase client (auth + storage)
│   │   ├── supabase_storage.py      — CV upload/download to Supabase bucket
│   │   ├── utils.py                 — Shared utilities
│   │   └── worker.py                — ARQ worker + CRON tasks
│   ├── providers/                   — Abstracted job data provider layer
│   │   ├── base.py                  — Abstract base provider interface
│   │   ├── jsearch.py               — JSearch RapidAPI provider
│   │   └── schemas.py               — Provider-agnostic job schemas
│   └── modules/
│       ├── auth/                    — register, login, logout, me
│       ├── CV/                      — upload, parse, embed, version history
│       ├── jobs/                    — live search, suggestion pool, fit scorer, queries
│       │   └── services/
│       │       ├── fit_scorer.py    — compute_fit_score (skill overlap + cosine)
│       │       ├── job_suggestion.py — suggestion pool build/advance/invalidate
│       │       ├── query_service.py — LLM query generation + fallback
│       │       ├── jsearch_parser.py — JSearch JSON → JobSchema
│       │       └── deduplicator.py  — raw job deduplication
│       ├── application/             — tracker, kanban, notes, status history
│       ├── chat/                    — conversations, sessions, messages, summarize, tools
│       ├── cover_letter/            — generate, CRUD drafts
│       ├── roadmap/                 — generate (from chat/job/manual), CRUD
│       ├── goals/                   — CRUD, from-roadmap promotion
│       └── notifications/           — WebSocket, DB, REST, Redis pub/sub
├── tests/
│   ├── conftest.py                  — (minimal; test DB setup pending)
│   └── test_api.py                  — 5 smoke tests (root, health, docs, openapi, auth guard)
├── feature.md                       — Detailed implementation reference
├── notification.md                  — Notification system architecture
├── ai.md                            — AI assistant (chat) guide
└── data.md                          — Test credentials
```

### Frontend

```
frontend/
├── src/
│   ├── main.jsx                     — React entrypoint
│   ├── App.jsx                      — Tab shell + WS lifecycle + header
│   ├── AuthContext.jsx              — Supabase auth state (login/logout/user)
│   ├── api.js                       — Full API client + createNotificationWS()
│   ├── index.css                    — Global styles (glass morphism design system)
│   └── components/
│       ├── Auth.jsx                 — Login / register form
│       ├── CV.jsx                   — Upload, version history, activate
│       ├── Jobs.jsx                 — Suggestion pool, live search, fit score cards
│       ├── Applications.jsx         — Kanban board, status changes, notes
│       ├── Chat.jsx                 — General + job-scoped coach chat
│       ├── CoverLetters.jsx         — Generate, view, edit drafts
│       ├── Roadmaps.jsx             — Roadmap list, phases, milestones
│       ├── Goals.jsx                — Goal CRUD, status tracking
│       ├── Notifications.jsx        — Notification history, mark read
│       └── ui.jsx                   — Shared UI primitives (Spinner, etc.)
├── dist/                            — Production build output
├── package.json                     — React 18 + Vite
└── vite.config.js                   — Dev server on port 3000
```

---

*Updated: 2026-06-09 | Branch: `ai_enhancement` | Hackathon: Codesprint 2026 by Poridhi.io*
