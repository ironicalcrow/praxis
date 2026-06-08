# Praxis — System Architecture

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │              React / Vite SPA  (port 3000)                   │  │
│   │                                                              │  │
│   │  Auth · CV · Jobs · Applications · Chat · Cover Letters      │  │
│   │  Roadmaps · Goals · Notifications                            │  │
│   └────────────────────────┬─────────────────────────────────────┘  │
│                            │  HTTP (REST)  +  WebSocket             │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                        API LAYER                                      │
│                                                                       │
│   ┌───────────────────────────────────────────────────────────────┐   │
│   │             FastAPI  (port 8000)                              │   │
│   │                                                               │   │
│   │  /api/auth   /api/cv     /api/jobs    /api/application        │   │
│   │  /api/chat   /api/roadmap /api/goals  /api/notifications      │   │
│   │  /api/cover-letter                                            │   │
│   │                                                               │   │
│   │  WS /ws/notifications                                         │   │
│   └───────────────────────────────────────────────────────────────┘   │
└──────────────┬─────────────────────┬─────────────────────────────────┘
               │                     │
       ┌───────▼──────┐     ┌────────▼────────┐
       │   ARQ Worker │     │  External APIs  │
       │  (background)│     │                 │
       └───────┬──────┘     │  Groq  (LLM)    │
               │            │  Jina  (embed)  │
               │            │  JSearch (jobs) │
               │            │  Supabase Auth  │
               │            └────────────────-┘
┌──────────────▼──────────────────────────────────────────────────────┐
│                        DATA LAYER                                    │
│                                                                      │
│   ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│   │   PostgreSQL      │   │  Redis (Upstash) │   │    Supabase    │  │
│   │   + pgvector      │   │                  │   │    Storage     │  │
│   │                   │   │  suggestion pool │   │                │  │
│   │  20 tables        │   │  job seen cache  │   │  cvs/ bucket   │  │
│   │  768-dim vectors  │   │  notif pub/sub   │   │  (PDF/DOCX/img)│  │
│   └──────────────────┘   └──────────────────┘   └────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Authentication Flow

```
  Browser                    FastAPI                   Supabase Auth
     │                          │                           │
     │── POST /api/auth/register ──▶                        │
     │                          │── supabase.auth.sign_up() ──▶
     │                          │                           │
     │                          │◀── user UUID + tokens ────│
     │                          │                           │
     │                          │  INSERT users (mirror row)│
     │◀── { access_token,        │                           │
     │      refresh_token }      │                           │
     │                          │                           │
     │── POST /api/auth/login ──▶│                           │
     │                          │── sign_in_with_password() ──▶
     │◀── { access_token } ──────│◀── JWT ───────────────────│
     │                          │                           │
     │── GET /api/cv/uploads     │                           │
     │   Authorization: Bearer <JWT>                        │
     │                          │                           │
     │                   decode JWT                         │
     │                   resolve user from local DB         │
     │◀── 200 OK ────────────────│                           │
```

> **Stateless.** JWTs are issued by Supabase and validated on every request. The local `users` table mirrors Supabase's `auth.users` by UUID.

---

## 3. CV Upload & AI Pipeline

```
  User uploads PDF / DOCX / image
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │  POST /api/cv/upload-cv                               │
  │                                                       │
  │  1. Read bytes → write to OS temp file                │
  │  2. Parse:                                            │
  │       PDF  →  PyMuPDF (fitz)                          │
  │       DOCX →  python-docx                             │
  │       IMG  →  EasyOCR (CPU)                           │
  │  3. ──── Groq LLM (llama-3.3-70b) ────────────────▶  │
  │       Prompt: "extract structured resume JSON"        │
  │       Returns: name, skills[], experience[],          │
  │                education[], projects[], certs[], YOE  │
  │  4. Upsert → resumes table (+ cascade skill rows)     │
  │  5. Upload original bytes → Supabase Storage          │
  │       cvs/{user_id}/{uuid}.ext                        │
  │  6. Insert cv_uploads row (is_active=True)            │
  │  7. Delete temp file                                  │
  └────────────────────────┬──────────────────────────────┘
                           │   Background (best-effort, non-blocking)
          ┌────────────────┼──────────────────────┐
          │                │                      │
          ▼                ▼                      ▼
   Jina Embed        Groq LLM              ARQ enqueue
   resume text   generate 5 search     collect_jobs_for_query
   → 768-dim vec  queries from CV       (one task per query)
   → resumes.     → job_queries +            │
     embedding      search_queries           ▼
                                      JSearch API scrape
                                      → embed each job
                                      → upsert jobs table
```

---

## 4. Job Suggestion Pool Engine

```
  GET /api/jobs/suggest-from-my-cv
          │
          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  Redis: suggestion_pool:{user_id}  exists?                       │
  └──────────┬──────────────────────────────┬───────────────────────┘
           HIT                             MISS
             │                               │
             │                   ┌───────────▼────────────────────┐
             │                   │  build_suggestion_pool()        │
             │                   │                                 │
             │                   │  1. Load resume_vec (768-dim)   │
             │                   │     + pref_vec if exists        │
             │                   │                                 │
             │                   │  2. Blend:                      │
             │                   │     user_vec = resume * 0.7     │
             │                   │              + pref   * 0.3     │
             │                   │                                 │
             │                   │  3. pgvector cosine search      │
             │                   │     ORDER BY distance ASC       │
             │                   │     WHERE posted_at > 30d ago   │
             │                   │     LIMIT 50                    │
             │                   │                                 │
             │                   │  4. For each job:               │
             │                   │     fit_score =                 │
             │                   │       skill_overlap * 50%       │
             │                   │     + cosine_sim    * 50%       │
             │                   │                                 │
             │                   │  5. Serialize → Redis (24h TTL) │
             │                   └───────────┬────────────────────-┘
             │                               │
             └───────────────────────────────┘
                                             │
                                             ▼
                             Return window[offset : offset+10]

  POST /api/jobs/suggest-from-my-cv/refresh  →  advance cursor by 10
          │
          ├─ 60% consumed?  →  enqueue ARQ prefetch (top 3 queries)
          └─ 100% consumed? →  reset offset=0 + background query regen
```

---

## 5. AI Career Coach Chat

```
  POST /api/chat/message  (or /api/chat/job/{id}/message)
          │
          ▼
  ┌────────────────────────────────────────────────────────┐
  │  Context Assembly  (~1,680 tokens total)               │
  │                                                        │
  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │
  │  │ System prompt│  │ Compressed CV │  │ Job context│  │
  │  │ + tool rules │  │ ~150 tokens   │  │ (job mode) │  │
  │  └──────────────┘  └───────────────┘  └────────────┘  │
  │                                                        │
  │  ┌─────────────────────┐  ┌──────────────────────────┐ │
  │  │ Last session summary│  │ Last 10 messages          │ │
  │  │ (cross-session mem) │  │ from current session      │ │
  │  └─────────────────────┘  └──────────────────────────┘ │
  └─────────────────────────┬──────────────────────────────┘
                            │
                            ▼
                  Groq LLM  (chatbot_caller.py)
                            │
               ┌────────────┴───────────────┐
               │                            │
           Direct reply               Tool call
               │                            │
               │              ┌─────────────▼────────────────┐
               │              │  Read tools (instant):        │
               │              │    search_jobs                │
               │              │    get_my_applications        │
               │              │    get_my_goals               │
               │              │    get_fit_score              │
               │              │                               │
               │              │  Write tools (confirm first): │
               │              │    generate_roadmap           │
               │              │    create_goals               │
               │              │    save_to_tracker            │
               │              │    draft_cover_letter         │
               │              └───────────────────────────────┘
               │
               ▼
       Save to chat_messages
       Return to client

  ─ ─ ─ ─ ─ ─ Session lifecycle ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

  Every 15 messages →  background summarize (LLM)
                    →  mark session inactive
                    →  create new session
                    →  inject summary into future context
                    →  push  conversation_summarized  via WS
                    →  push  coach_roadmap_nudge  if skill gap found
```

---

## 6. Real-Time Notification System

```
  Any module (CV, jobs, chat, etc.)
          │
          │  await create_and_publish(user_id, type, title, message)
          ▼
  ┌─────────────────────────────────────────────────────────┐
  │  notification.service.create_and_publish()              │
  │                                                         │
  │  1. INSERT into notifications table  (always persisted) │
  │  2. Serialize to JSON payload                           │
  │  3. Redis PUBLISH → channel: user:{user_id}:notifications│
  └──────────────────────────┬──────────────────────────────┘
                             │
                             │  Redis pub/sub
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  NotificationManager._redis_listener()                  │
  │  (one asyncio Task per connected WebSocket)             │
  │                                                         │
  │   SUBSCRIBE user:{user_id}:notifications                │
  │       │                                                 │
  │       └── on message → websocket.send_text(payload)     │
  └──────────────────────────┬──────────────────────────────┘
                             │  WebSocket frame
                             ▼
                    Browser  (frontend/src/api.js)
                    createNotificationWS() → live toast


  ─ ─ ─ ─ ─ ─ Offline catch-up ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

  On WS connect:  GET /api/notifications?unread_only=true
                  → push all undelivered notifications
                  → client marks them read on view
```

---

## 7. Background Worker (ARQ)

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                        ARQ Worker Process                        │
  │                                                                  │
  │  Redis queue (Upstash) ──▶ dequeue tasks ──▶ execute            │
  │                                                                  │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  CRON SCHEDULE                                           │   │
  │  │                                                          │   │
  │  │  collect_jobs          every 6h  (00:00, 06:00, 12:00,  │   │
  │  │                                   18:00)                 │   │
  │  │    └─ find stale SearchQueries                           │   │
  │  │    └─ JSearch API (3-key rotation, 200 jobs / query)     │   │
  │  │    └─ Jina embed each job (semaphore: max 2 concurrent)  │   │
  │  │    └─ upsert jobs table                                  │   │
  │  │                                                          │   │
  │  │  clean_expired_jobs    daily @ 01:00                     │   │
  │  │    └─ delete orphaned SearchQuery rows                   │   │
  │  │    └─ delete jobs not refreshed in 7 days                │   │
  │  │                                                          │   │
  │  │  prune_chat_messages   weekly Sunday @ 02:00             │   │
  │  │    └─ keep last 2 sessions per conversation              │   │
  │  │    └─ delete older raw messages (summaries kept)         │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  ON-DEMAND TASKS  (enqueued by API)                      │   │
  │  │                                                          │   │
  │  │  collect_jobs_for_query(query, location, sq_id)          │   │
  │  │    └─ triggered on: CV upload, CV activate,              │   │
  │  │                     live search (stale), pool prefetch   │   │
  │  └──────────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 8. Data Model (Core Tables)

```
  ┌──────────┐        ┌───────────────┐       ┌─────────────────┐
  │  users   │───1:1──│   resumes     │       │  user_prefs     │
  │          │        │               │       │  (job_types[])  │
  │  id UUID │        │  embedding    │       │  pref_embedding │
  │  email   │        │  (vector 768) │       └─────────────────┘
  └────┬─────┘        └───────┬───────┘
       │                      │ 1:N
       │              ┌───────┴──────────────────────────────────┐
       │              │  resume_skills  resume_education          │
       │              │  resume_experience  resume_projects       │
       │              │  resume_certifications                    │
       │              └───────────────────────────────────────────┘
       │
       ├──────1:N──── cv_uploads  (version history, is_active)
       │
       ├──────1:N──── applications
       │                 └─ application_status_history
       │                 └─ application_notes
       │
       ├──────1:N──── chat_conversations
       │                 └─ chat_sessions  (summary, is_active)
       │                       └─ chat_messages
       │
       ├──────1:N──── roadmaps
       │                 └─ roadmap_phases
       │                       └─ roadmap_milestones
       │
       ├──────1:N──── goals
       │
       ├──────1:N──── notifications  (type, is_read, data JSON)
       │
       └──────1:N──── job_queries  ────M:N──── search_queries ────M:N──── jobs
                                                                           │
                                                                  embedding (vector 768)
                                                                  posted_at, skills[]
                                                                  apply_urls[]
```

---

## 9. External Service Dependency Map

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                         Praxis Backend                           │
  │                                                                  │
  │   llm_caller.py ──────────────────────────────▶  Groq API       │
  │   (CV parse, query gen, fit score, roadmap,        llama-3.3-    │
  │    session summarize)                              70b-versatile │
  │                                                                  │
  │   chatbot_caller.py ──────────────────────────▶  Groq API       │
  │   (chat messages, tool orchestration)             (separate key) │
  │                                                                  │
  │   llm_caller.embed_text() ────────────────────▶  Jina AI        │
  │   (resume embed, job embed, pref embed)           jina-          │
  │                                                   embeddings-    │
  │                                                   v2-base-en     │
  │                                                   768-dim        │
  │                                                                  │
  │   providers/jsearch.py ────────────────────────▶  JSearch API   │
  │   (live search, background scrape)                (RapidAPI)     │
  │                                                   3-key rotation │
  │                                                                  │
  │   supabase.py ─────────────────────────────────▶  Supabase Auth │
  │   (register, login, JWT validation)                              │
  │                                                                  │
  │   supabase_storage.py ─────────────────────────▶  Supabase      │
  │   (CV upload/download)                             Storage       │
  │                                                    cvs/ bucket   │
  │                                                                  │
  │   session.py ──────────────────────────────────▶  PostgreSQL    │
  │   (SQLAlchemy, pgvector)                           (Supabase     │
  │                                                    hosted)       │
  │                                                                  │
  │   worker.py / notifications ───────────────────▶  Redis         │
  │   (ARQ queue, pub/sub, suggestion pool cache)      (Upstash TLS) │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 10. Request Lifecycle (end-to-end example: "get job suggestions")

```
  Browser
    │
    ├─ 1. GET /api/jobs/suggest-from-my-cv
    │       Authorization: Bearer <JWT>
    │
  FastAPI
    │
    ├─ 2. get_current_user() — decode JWT, resolve user from DB
    │
    ├─ 3. Fetch active resume from DB
    │
    ├─ 4. Redis GET suggestion_pool:{user_id}
    │        │
    │        ├─ HIT  →  return pool[offset : offset+10]
    │        │
    │        └─ MISS →  build_suggestion_pool()
    │                       │
    │                       ├─ Load resume_vec + pref_vec from DB
    │                       ├─ pgvector: SELECT jobs ORDER BY
    │                       │            cosine_distance ASC LIMIT 50
    │                       ├─ compute fit_score per job (Python)
    │                       └─ Redis SETEX 86400s → return [0:10]
    │
    ├─ 5. Return JSON  { jobs: [...10 items...], jobs_seen, pool_total }
    │
  Browser
    │
    └─ 6. Render job cards with fit score + verdict
```

---

*Generated: 2026-06-09 | Praxis — Codesprint 2026 by Poridhi.io*
