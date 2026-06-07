# Praxis Backend — Implementation Reference

This document explains exactly how the system works, end-to-end, at a low level. Every trigger point, Redis key, DB table, and decision branch is described.

---

## System Overview

Praxis is a job search backend that:
1. Parses a user's CV with an LLM
2. Generates job search queries from the CV content
3. Scrapes jobs from JSearch in the background (ARQ worker)
4. Stores jobs in PostgreSQL with pgvector embeddings
5. Serves a personalized suggestion pool ranked by semantic + skill fit
6. Lets users refresh, cycle, and influence suggestions through their actions

**Stack:** FastAPI · PostgreSQL + pgvector · Upstash Redis · ARQ (background worker) · Supabase Auth + Storage · Jina AI (embeddings) · Groq (LLM) · JSearch RapidAPI

---

## 1. Authentication

**Provider:** Supabase Auth (cloud). JWTs are issued by Supabase, not our backend.

**Register** `POST /api/auth/register`
- Checks local `users` table for duplicate email/username first
- Calls `supabase.auth.sign_up()` — creates user in Supabase's `auth.users` table
- On success, inserts a mirrored row into our local `users` table using the same UUID Supabase assigned
- If email confirmation is required (Supabase setting), returns 201 with a "verify email" message instead of tokens

**Login** `POST /api/auth/login`
- Calls `supabase.auth.sign_in_with_password()`
- Returns `access_token` + `refresh_token` from Supabase
- No local session state — stateless JWT

**Every protected endpoint** — `get_current_user` dependency decodes the JWT and resolves the user from the local `users` table. Auth lives entirely in Supabase; local DB just mirrors the user record.

---

## 2. CV Upload

**Trigger:** `POST /cv/upload-cv` (multipart file upload)

**Step-by-step:**

```
1. Read all file bytes into memory (await file.read())
2. Write to OS temp dir via tempfile.NamedTemporaryFile — NO local uploads/ folder
3. Parse the temp file:
   - PDF → PyMuPDF (fitz) text extraction
   - DOCX → python-docx paragraph join
   - PNG/JPG → EasyOCR (CPU mode)
4. Send extracted text to Groq LLM (llama-3.3-70b-versatile) via call_llm()
   - Prompt: "extract structured resume JSON"
   - Returns: name, email, phone, location, skills[], education[], experience[],
              projects[], certifications[], years_of_experience
5. Save parsed resume to DB → resumes table (upsert by user_id — one row per user)
   - Also clears and rewrites: resume_skills, resume_education, resume_experience,
     resume_projects, resume_certifications (cascade delete + re-insert)
6. Upload original file bytes to Supabase Storage:
   - Bucket: cvs (configurable via SUPABASE_STORAGE_BUCKET env)
   - Path: {user_id}/{uuid}{extension}
   - Returns public URL
7. Insert row into cv_uploads: (id, user_id, file_url, storage_path, original_filename,
   is_active=True, uploaded_at)
   - All previous cv_uploads rows for this user → is_active=False (only one active at a time)
8. Update resumes.file_url = new Supabase URL
9. Delete the OS temp file (in finally block — always runs even on error)
10. Best-effort background steps (each wrapped in try/except — failure never blocks response):
    a. Build resume text string → call Jina embeddings API → save vector to resumes.embedding
    b. Call LLM to generate 5 job search queries → save as JobQuery rows → enqueue each
       to ARQ worker (collect_jobs_for_query task)
    c. Delete suggestion pool from Redis (suggestion_pool:{user_id}, suggestion_offset:{user_id})
       so the next GET /suggest rebuilds fresh
```

**DB tables touched:** `resumes`, `resume_skills`, `resume_education`, `resume_experience`, `resume_projects`, `resume_certifications`, `cv_uploads`, `job_queries`, `search_queries`

**Redis keys written:** `suggestion_pool:{user_id}` deleted, `suggestion_offset:{user_id}` deleted

**Supabase uploads path:** `cvs/{user_id}/{uuid}.pdf`

**Fault tolerance:** If Supabase upload fails → CV still saved, `file_url=null`, warning logged. If embedding fails → resume saved without vector, suggestions fall back to recency sort. If LLM query generation fails → skill-based fallback queries used.

---

## 3. CV Upload History & Activation

### List past uploads
**Trigger:** `GET /cv/uploads`
- Queries `cv_uploads` table filtered by `user_id`, ordered by `uploaded_at DESC`
- Returns list of: id, file_url, original_filename, is_active, uploaded_at

### Activate a past CV
**Trigger:** `POST /cv/uploads/{upload_id}/activate`

This lets the user switch to any previously uploaded CV. The system re-runs the full parse+embed+query flow against the old file.

```
1. Fetch cv_uploads row by (upload_id + user_id) — 404 if not found or not owned by user
2. Download file bytes from Supabase Storage using storage_path
3. Write bytes to OS temp file (tempfile — no local retention)
4. Re-parse the file with resume_parser() → same LLM extraction as upload
5. Upsert the resumes row with the new parsed content + keep the same file_url
6. cv_uploads: set all rows is_active=False, then set this upload's is_active=True
7. Delete OS temp file (finally block)
8. Best-effort background steps (same as upload):
   a. Re-embed the resume
   b. Regenerate job queries + enqueue scraping
   c. Invalidate suggestion pool
```

**Effect:** After activation, the user's suggestions, fit scores, and queries all reflect the re-activated CV's content.

---

## 4. Embeddings

**Provider:** Jina AI (free tier, 768-dimensional vectors)

**Concurrency limit:** Jina's free tier allows 2 concurrent embedding requests. A global `asyncio.Semaphore(2)` named `_embedding_sem` in `tasks.py` is shared across all ARQ worker coroutines to enforce this. The API will 429 if you exceed it.

**What gets embedded:**

| Entity | Text sent to Jina |
|---|---|
| Resume | `"Location: X. Skills: A, B, C. [raw_text[:500]] Role at Org: desc."` |
| Job | `"Title Company Skills: A, B. [llm_summary]"` |
| User preferences | `"Preferred job types: Remote, Full-time"` |

**Vector stored in:** `resumes.embedding` (Vector 768), `jobs.embedding` (Vector 768), `user_preferences.preference_embedding` (Vector 768)

**Embedding dimensions:** Configured via `EMBEDDING_DIMENSIONS` in `.env` (default: 1536, but Jina returns 768). The vector columns are set to `vector(768)`.

---

## 5. Job Query Generation

**Trigger:** After CV upload/activation, or when `POST /jobs/queries/refresh` is called

**Function:** `refresh_resume_job_queries(resume_id, resume_obj)`

```
1. Extract from the ResumeSchema:
   - skills (e.g. ["Python", "FastAPI", "PostgreSQL"])
   - past roles from experience (e.g. ["Backend Engineer", "Software Developer"])
   - education degrees
   - location (resume.location or resume.country or "Any")
2. Build LLM prompt asking for 5 diverse job search queries as JSON array
   Each query has: { query, priority (1-5), reason }
3. Call Groq LLM → parse JSON response
   If LLM fails → _skill_fallback(): generates basic queries directly from skills[]
4. For each generated query:
   a. _get_or_create_search_query(db, query_string, location)
      → hashes (query+location) to find or create a SearchQuery row
   b. Upsert a JobQuery row linking this resume to that SearchQuery
      (priority, reason, added_at)
   c. Enqueue ARQ task: collect_jobs_for_query(query, location, search_query_id)
```

**DB tables:** `search_queries` (global, shared across users), `job_queries` (per-user-resume link)

**Priority:** LLM assigns 1–5. Higher priority queries are shown first in GET /jobs/queries.

---

## 6. Background Worker (ARQ)

**Config:** `WorkerSettings` in `app/core/worker.py`
- Functions registered: `collect_jobs`, `collect_jobs_for_query`, `clean_expired_jobs`
- CRON: `collect_jobs` every 6 hours (00:00, 06:00, 12:00, 18:00)
- CRON: `clean_expired_jobs` daily at 01:00

### `collect_jobs_for_query` (instant queue)
**Trigger:** Enqueued immediately after query generation or live search on a stale query

```
Input: query (str), location (str|None), search_query_id (str|None)

1. Call JSearch API: search_jobs(query, location, limit=200, num_pages=20)
   - Full query string built as: "{query} in {location}" (avoids duplication)
   - If location already in query string → don't append
2. If 0 results → fallback: search_jobs(query, location="", limit=50)
   (global remote search — catches remote jobs everywhere)
3. Deduplicate raw results: deduplicate_raw_jobs() hashes (provider_id + job_id)
4. For each unique raw job → _process_and_save_job(raw_job, r, sem)
```

### `_process_and_save_job(raw_job, r, sem)` (shared module-level helper)

```
1. Redis check: r.exists("seen_job:{provider_id}:{job_id}")
   If exists → skip entirely (job processed within last 48h)
   If Redis is down → proceed anyway (fault tolerant)
2. Acquire _embedding_sem (max 2 concurrent Jina calls)
3. parse_jsearch_to_schema(raw_job) → maps raw JSearch JSON to JobSchema
   Extracts: title, company, location, description, skills[], job_types[],
   responsibilities[], qualifications[], apply_urls[], posted_at
4. Build embedding input string → call Jina embed_text()
   If embedding fails → embedding_vector = None (job saved without vector)
5. _save_job_to_db(schema, vector, search_query_id):
   - If job (external_id + provider_id) exists → update updated_at + embedding
   - If new → insert Job row with all fields
   - Link job to SearchQuery via search_query_jobs association table
6. r.set("seen_job:{provider_id}:{job_id}", "1", ex=48h)
   Prevents re-processing the same job for 48 hours
```

### `collect_jobs` (CRON — every 6 hours)

```
1. Query SearchQuery rows where last_run_at IS NULL or last_run_at < 24h ago (stale)
2. For each stale query → call JSearch API concurrently (asyncio.gather)
3. Update last_run_at = now for successful queries
4. Merge all results → deduplicate → process each via _process_and_save_job
5. Remote fallback for any query that returned 0 results
```

### `clean_expired_jobs` (CRON — daily 01:00)

```
1. Find SearchQuery IDs that are still referenced by at least one JobQuery
   (i.e., at least one user still has this query)
2. Delete SearchQuery rows NOT in that list (orphaned — no users care about them)
3. Delete Job rows where updated_at < 48h ago
   (jobs not refreshed by the CRON within 48h are considered expired)
```

---

## 7. Suggestion Pool

This is the core of the recommendation system. Instead of computing suggestions on every request, we pre-build a pool of 50 jobs, show 10 at a time, and manage a cursor.

**Constants:**
- `POOL_SIZE = 50` — jobs pre-ranked and stored per user
- `WINDOW_SIZE = 10` — jobs shown per request
- `PREFETCH_THRESHOLD = 0.6` — at 60% consumed, fire background scrape
- `POOL_TTL_SECONDS = 86400` — pool expires after 24h
- `RECENCY_DAYS = 30` — only include jobs posted within 30 days (or posted_at IS NULL)

**Redis keys per user:**
- `suggestion_pool:{user_id}` — JSON array of up to 50 JobSchema dicts (with fit_scores embedded)
- `suggestion_offset:{user_id}` — integer cursor, tracks how many jobs the user has seen

### Building the pool: `build_suggestion_pool(user_id, candidate_resume, queries)`

```
1. Fetch from DB:
   - resumes.embedding → resume vector (768-dim)
   - user_preferences.preference_embedding → preference vector (768-dim)

2. Compute user_vector:
   - If both vectors exist: user_vector = resume_vec * 0.7 + pref_vec * 0.3 (numpy blend)
   - If only resume vector: user_vector = resume_vec
   - If no vector at all: generate on-the-fly from resume text → call Jina → save to DB

3. pgvector semantic search:
   SELECT jobs, cosine_distance(jobs.embedding, user_vector) AS dist
   FROM jobs
   WHERE jobs.embedding IS NOT NULL
     AND (jobs.posted_at >= 30_days_ago OR jobs.posted_at IS NULL)
   ORDER BY dist ASC
   LIMIT 50

   If pgvector fails → fallback: ORDER BY posted_at DESC LIMIT 50 (no vector)

4. If DB returns 0 jobs (fresh system, no scraping yet):
   → Live JSearch fallback: call JSearch for queries[0], parse results, build pool from
     live data (no fit_score computed — just raw jobs). Store in Redis and return.

5. For each (job, cosine_dist) pair:
   - semantic_similarity = max(0.0, 1.0 - cosine_dist)
   - Compute fit score: compute_fit_score(profile, resume, semantic_similarity)
     → skill_score = overlap / job_skills * 100  (0-100)
     → final_score = skill_score * 0.5 + semantic_similarity * 100 * 0.5
     → Produces: { fit_score, verdict, reason, strengths[], weaknesses[] }

6. Serialize all jobs + fit_scores to JSON array

7. Store in Redis:
   r.setex("suggestion_pool:{user_id}", 86400, json.dumps(pool))
   r.set("suggestion_offset:{user_id}", 0)

8. Return first window (pool[0:10])
```

### Getting the current window: `get_suggestion_window(user_id)`

```
1. Read Redis: pool_raw, offset
2. If pool_raw is None → return None (caller must build pool)
3. Parse JSON → return pool[offset : offset + 10]
   (idempotent — doesn't advance cursor)
```

**Trigger:** `GET /jobs/suggest-from-my-cv`
- If window returned → send it
- If None → call `build_suggestion_pool()` first, then return window

### Advancing the window: `advance_suggestion_window(user_id, queries, resume, resume_id)`

```
1. Read pool + current offset from Redis
2. new_offset = offset + 10

3. Prefetch check (60% threshold):
   if new_offset / pool_size >= 0.6:
     → Enqueue collect_jobs_for_query for top 3 queries via ARQ
     → prefetch_triggered = True in response

4. Pool exhaustion check (100% consumed):
   if new_offset >= pool_size:
     → new_offset = 0 (cycle back to beginning)
     → pool_cycling = True in response
     → asyncio.create_task(refresh_resume_job_queries()) — regenerate queries in background

5. Write new_offset back to Redis
6. Return window: pool[new_offset : new_offset + 10]
   + { jobs_seen, pool_total, prefetch_triggered, pool_cycling }
```

**Trigger:** `POST /jobs/suggest-from-my-cv/refresh`

### Pool invalidation

Pool is wiped (both Redis keys deleted) when:
- New CV uploaded (`POST /cv/upload-cv`)
- Past CV activated (`POST /cv/uploads/{id}/activate`)
- Preferences updated (`PUT /jobs/preferences`)
- Live search on a stale query (`POST /jobs/live-search` when `is_stale=True`)

---

## 8. Fit Score

**Function:** `compute_fit_score(profile, candidate, semantic_similarity=None)`

```
Inputs:
  profile: JobRequirementProfile (job's required_skills, qualifications, responsibilities, etc.)
  candidate: ResumeSchema (user's skills list)
  semantic_similarity: float 0.0-1.0 from pgvector, or None

Skill overlap:
  job_skills = set(profile.required_skills + profile.tools_and_technologies)
  candidate_skills = set(candidate.skills)
  overlap = job_skills ∩ candidate_skills (case-insensitive)
  skill_score = len(overlap) / len(job_skills) * 100   (or 65.0 if no job skills listed)

Final score:
  If semantic_similarity is provided:
    score = skill_score * 0.5 + (semantic_similarity * 100) * 0.5
  If not:
    score = skill_score   (skill-only, used in detail view and live search)

score = clamp(score, 0, 100)

Verdict:
  90+  → "Excellent Match"
  75+  → "Strong Match"
  60+  → "Good Match"
  45+  → "Moderate Match"
  else → "Low Match"

Returns: { fit_score, verdict, reason, strengths[], weaknesses[] }
```

**Where semantic_similarity IS used:** Suggestion pool (pgvector distance available)
**Where it is NOT used:** Job detail view, live search results (no distance computed in those paths)

---

## 9. User Preferences

**What's stored:** Only `job_types` — an enum list (Full-time, Part-time, Contract, Internship, Freelance, Remote, Hybrid, On-site)

**No location/country in preferences** — location comes from the resume (`resumes.location` / `resumes.country`)

**Trigger:** `PUT /jobs/preferences`

```
1. Validate job_types against JobTypeEnum
2. Upsert user_preferences row (one per user)
3. Best-effort preference embedding:
   - pref_text = "Preferred job types: Remote, Full-time"
   - Call Jina embed_text() → save to user_preferences.preference_embedding
   If this fails → preferences still saved, just without vector signal
4. Invalidate suggestion pool (async_invalidate_pool)
   Next GET /suggest rebuilds with blended vector (resume 70% + pref 30%)
```

**Effect on suggestions:** The blended vector `resume * 0.7 + pref * 0.3` shifts ranking toward jobs that semantically match the stated work arrangement preferences.

---

## 10. Live Search

**Trigger:** `POST /jobs/live-search`

```
Input: { query, location, page, num_pages, country, remote_jobs_only }

1. Fetch user preferences (for context, no location used from there)
2. _get_or_create_search_query(db, query, target_loc)
   → hash(query+location) → find or create SearchQuery row
3. Staleness check:
   - If last_run_at IS NULL or last_run_at > 24h ago → is_stale = True
   - If last_run_at < 24h ago → is_stale = False (HOT — skip API call)
4. Upsert JobQuery for this user+query (priority=10, reason="user searched")
   If user has 10+ queries → evict lowest priority one
5. Manual search threshold: if user has 5+ "user searched" queries
   → fire asyncio.create_task(refresh_resume_job_queries) in background
6. If is_stale:
   a. Enqueue collect_jobs_for_query to ARQ worker (background scrape)
   b. Invalidate suggestion pool (new data incoming)
   If NOT stale → pool is left untouched (HOT query, no new data)
7. Embed the query string → pgvector similarity search in jobs table
   (concurrent with step 8 via asyncio.gather)
8. If page==1 and is_stale → also hit JSearch live for instant results (limit=10)
9. Merge DB results + live results (dedup by job_id)
   Live jobs: cached in Redis as temp_job:{job_id} for 2 hours
10. Return merged list (no fit_score — live search is raw results by design)
```

---

## 11. Job Detail

**Trigger:** `GET /jobs/details/{job_id}`

```
1. Look up job by external_id or id in the jobs table
2. If found in DB:
   - Map to JobSchema
   - Compute fit_score (skill-only, no semantic_similarity — no distance available here)
   - Return
3. If not in DB:
   - Check Redis: temp_job:{job_id} (live search cache, 2h TTL)
   - If found → parse the cached raw job → compute fit_score → embed it → save to DB
   - If not found → raise 404
```

---

## 12. Health Check

**Trigger:** `GET /health` (no auth required)

```
1. Try: execute "SELECT 1" against PostgreSQL
2. Try: PING Upstash Redis
3. Return: { db: "ok"|"error: ...", redis: "ok"|"error: ...", status: "healthy"|"degraded" }
```

---

## 13. Fault Tolerance Summary

| Failure | What happens |
|---|---|
| Jina embedding fails (CV) | Resume saved without vector; suggestions use recency sort |
| Jina embedding fails (job in worker) | Job saved without vector; not returned in pgvector search, but visible in recency fallback |
| Groq LLM fails (query generation) | Skill-based fallback queries used (top 5 skills as raw search terms) |
| Groq LLM fails (CV parsing) | 502 error returned — CV parse is the one step that must succeed |
| JSearch all 3 keys rate-limited | Returns [], worker logs it, CRON retries next cycle |
| Supabase Storage upload fails | CV saved to DB, file_url=null, warning logged |
| Redis unavailable | Cache miss — falls through to DB. Pool invalidation silently skipped. |
| pgvector search fails | Falls back to ORDER BY posted_at DESC |
| DB empty (no jobs scraped yet) | Suggestion pool seeded with 5–10 live JSearch results |
| Worker offline during prefetch | Enqueue fails silently; pool cycling still works from existing pool |

---

## 14. Data Flow Summary

```
User uploads CV
  → Temp file (OS) → LLM parse → DB (resumes)
  → Supabase Storage (cvs/{user_id}/{uuid}.pdf) → DB (cv_uploads.is_active=True)
  → Jina embed → DB (resumes.embedding)
  → Groq LLM → 5 search queries → DB (job_queries, search_queries)
  → ARQ queue → Worker → JSearch (200 jobs, 20 pages) → Jina embed each → DB (jobs)

User visits suggestions
  → Redis check (suggestion_pool:{user_id})
  → Miss → pgvector search (cosine distance, recency filter)
    → blend resume_vec*0.7 + pref_vec*0.3
    → compute fit_score (skill overlap 50% + cosine similarity 50%) per job
    → store 50 jobs in Redis → return first 10

User refreshes suggestions (POST /refresh)
  → Read Redis pool + offset
  → Advance cursor by 10
  → 60% consumed? → enqueue ARQ scrape (prefetch)
  → 100% consumed? → cycle to 0 + background LLM query regen
  → Return next 10 jobs

User updates preferences
  → DB upsert → Jina embed job_types string → DB (preference_embedding)
  → Invalidate Redis pool → next suggest rebuilds with blended vector

User live searches
  → HOT query? → DB pgvector + instant JSearch results (no pool wipe)
  → STALE query? → enqueue ARQ + wipe pool + DB pgvector + instant JSearch

ARQ CRON (every 6h)
  → Find stale SearchQueries → JSearch → embed → upsert jobs

ARQ CRON (daily 01:00)
  → Delete orphaned SearchQueries → delete jobs older than 48h
```

---

## 15. Key Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `LLM_MODEL` | Groq model (llama-3.3-70b-versatile) |
| `LLM_BASE_URL` | https://api.groq.com/openai/v1 |
| `EMBEDDING_MODEL` | Jina model name |
| `EMBEDDING_DIMENSIONS` | 768 for Jina |
| `JSEARCH_API_KEYS` | Comma-separated keys for rotation |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | For storage operations |
| `SUPABASE_STORAGE_BUCKET` | `cvs` (default) |
| `REDIS_URL` | Upstash TLS URL (`rediss://...`) |
| `DATABASE_URL` | PostgreSQL connection string |
