# PRAXIS — Endpoint Testing Guide

Manual test guide for **every endpoint in the system**: 63 HTTP routes across 9
routers, plus 1 WebSocket. Each entry has a ready-to-paste curl, filled-in sample
data, and the expected response.

An importable Postman collection covering the same surface ships alongside this
file: [`praxis.postman_collection.json`](praxis.postman_collection.json).

> Scope note: the automated suite in [`tests/`](tests/README.md) covers the
> **goals, roadmap, and notifications** routers. This document covers the whole
> system, so most of what follows is not yet under automated test. Endpoints with
> a known defect are cross-referenced to [`BUG_REPORT.md`](BUG_REPORT.md).

---

## Setup

Start the API:

```bash
make dev                                    # api + worker + frontend
# or just the API:
cd backend && ../backend/.venv/bin/uvicorn main:app --reload
```

Shared shell variables — every example below assumes these:

```bash
export BASE=http://localhost:8000
export EMAIL=tester@example.com
export PASSWORD=Sup3rSecret!
```

### Get a token

Auth is delegated to Supabase; the API mints nothing itself. Register once, then
log in to obtain a token for every other call.

```bash
# 1. Register (only needed once)
curl -s -X POST "$BASE/api/auth/register" -H 'Content-Type: application/json' -d '{
  "name": "Test Tester",
  "username": "tester",
  "email": "'"$EMAIL"'",
  "password": "'"$PASSWORD"'"
}'

# 2. Log in and capture the token
export TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

export AUTH="Authorization: Bearer $TOKEN"
export JSON="Content-Type: application/json"

# 3. Capture your user id — the application endpoints need it explicitly
export USER_ID=$(curl -s "$BASE/api/auth/me" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
```

Verify the token works:

```bash
curl -s "$BASE/api/auth/me" -H "$AUTH"
# {"id":"…","email":"tester@example.com","name":"Test Tester","username":"tester"}
```

### Conventions that will trip you up

| Thing | Detail |
|---|---|
| Trailing slashes | Collection routes are registered as `""` → use `/api/goals`, **not** `/api/goals/` (307). The one exception is `/api/cover-letter/`, which is the opposite way round. See [GOALS-07](BUG_REPORT.md#goals-07). |
| Missing token | Returns **401**, not 403. |
| `application` router | Takes **no** `Authorization` header at all — `user_id` goes in the body or query string. |
| Path ids | Typed `UUID` almost everywhere → a non-UUID gives **422**, not 404. Exception: `cover_letter_id` is a plain `str`. |
| 204 responses | Return an empty body. `curl` prints nothing — use `-w '%{http_code}'`. |

---

## 1. System — 2 endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/` | no |
| GET | `/health` | no |

```bash
curl -s "$BASE/"
# {"message":"Praxis server is running"}

curl -s "$BASE/health"
# {"db":"ok","redis":"ok","status":"healthy"}
```

`/health` never 500s — it reports `"status":"degraded"` with per-dependency
detail when Postgres or Redis is unreachable. Useful as a first check when
something else misbehaves.

Also available: `/docs` (Swagger UI) and `/openapi.json`.

---

## 2. Authentication — 4 endpoints

| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/api/auth/register` | no | `RegisterRequest` |
| POST | `/api/auth/login` | no | `LoginRequest` |
| POST | `/api/auth/logout` | no | — |
| GET | `/api/auth/me` | **yes** | — |

```bash
# Register — name ≥2, username ≥3, password ≥8 chars
curl -s -X POST "$BASE/api/auth/register" -H "$JSON" -d '{
  "name": "Test Tester", "username": "tester",
  "email": "tester@example.com", "password": "Sup3rSecret!"
}'
# 200 {"access_token":"…","refresh_token":"…","token_type":"bearer","user":null}

# Login
curl -s -X POST "$BASE/api/auth/login" -H "$JSON" \
  -d '{"email":"tester@example.com","password":"Sup3rSecret!"}'
# 200 {"access_token":"…","refresh_token":"…","token_type":"bearer","user":{…}}

# Current user
curl -s "$BASE/api/auth/me" -H "$AUTH"

# Logout
curl -s -X POST "$BASE/api/auth/logout"
# 200 {"message":"Logged out successfully"}
```

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Duplicate username | register with an existing `username` | 400 `"Username already exists"` |
| Duplicate email | register with an existing `email` | 400 `"Email already exists"` |
| Short password | `"password":"short"` | 422 |
| Wrong password | login with a bad password | 401 `"Invalid email or password"` |
| No token | `GET /api/auth/me` without header | 401 |
| Bad token | `-H "Authorization: Bearer nope"` | 401 |

> Two behaviours worth knowing when reading responses here. If Supabase requires
> email confirmation, register returns **201 with a `detail` message and no
> tokens** — a 2xx that is actually a failure for the caller. And login converts
> *every* exception to 401, so a Supabase outage is reported as "Invalid email or
> password". Neither is covered by the automated suite (out of scope).

---

## 3. CV — 4 endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/cv/upload-cv` | yes | multipart |
| GET | `/api/cv/my-cv` | yes | |
| GET | `/api/cv/uploads` | yes | |
| POST | `/api/cv/uploads/{upload_id}/activate` | yes | |

```bash
# Upload — .pdf .docx .png .jpg .jpeg only, matched on FILENAME EXTENSION
curl -s -X POST "$BASE/api/cv/upload-cv" -H "$AUTH" -F "file=@/path/to/resume.pdf"
# 200 {"success":true,"message":"CV uploaded, parsed, and saved successfully",
#      "resume_id":"…","file_url":"…","data":{…parsed resume…}}

curl -s "$BASE/api/cv/my-cv" -H "$AUTH"
curl -s "$BASE/api/cv/uploads" -H "$AUTH"

export UPLOAD_ID=$(curl -s "$BASE/api/cv/uploads" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
curl -s -X POST "$BASE/api/cv/uploads/$UPLOAD_ID/activate" -H "$AUTH"
```

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Unsupported format | `-F "file=@notes.txt"` | 400 `"Unsupported file format"` |
| No CV uploaded yet | `GET /api/cv/my-cv` | 404 |
| Unknown upload id | activate a random UUID | 404 `"Upload not found"` |
| Storage down | activate when Supabase is unreachable | 502 |

This endpoint is slow — it parses, calls an LLM, embeds, and generates job
queries **inline** before responding. Expect 10–30s. There is no upload size
limit, and the whole file is read into memory.

---

## 4. Jobs — 9 endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/jobs/live-search` | yes |
| GET | `/api/jobs/details/{job_id}` | yes |
| GET | `/api/jobs/details/{job_id}/status` | yes |
| GET | `/api/jobs/suggest-from-my-cv` | yes |
| POST | `/api/jobs/suggest-from-my-cv/refresh` | yes |
| GET | `/api/jobs/queries` | yes |
| POST | `/api/jobs/queries/refresh` | yes |
| GET | `/api/jobs/preferences` | yes |
| PUT | `/api/jobs/preferences` | yes |

```bash
curl -s -X POST "$BASE/api/jobs/live-search" -H "$AUTH" -H "$JSON" -d '{
  "query": "backend engineer",
  "location": "Dhaka",
  "page": 1,
  "num_pages": 1,
  "country": "bd"
}'
# 200 {"query":"backend engineer","total":10,"jobs":[…]}

export JOB_ID=$(curl -s -X POST "$BASE/api/jobs/live-search" -H "$AUTH" -H "$JSON" \
  -d '{"query":"backend engineer"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["jobs"][0]["id"])')

curl -s "$BASE/api/jobs/details/$JOB_ID" -H "$AUTH"
curl -s "$BASE/api/jobs/details/$JOB_ID/status" -H "$AUTH"
# {"job_id":"…","in_tracker":false,"application_id":null,"application_status":null,
#  "has_cover_letter":false,"cover_letter_id":null,"has_chat":false,"conversation_id":null}

curl -s "$BASE/api/jobs/suggest-from-my-cv" -H "$AUTH"          # idempotent
curl -s -X POST "$BASE/api/jobs/suggest-from-my-cv/refresh" -H "$AUTH"   # advances cursor

curl -s "$BASE/api/jobs/queries" -H "$AUTH"
curl -s -X POST "$BASE/api/jobs/queries/refresh" -H "$AUTH"

curl -s "$BASE/api/jobs/preferences" -H "$AUTH"
curl -s -X PUT "$BASE/api/jobs/preferences" -H "$AUTH" -H "$JSON" \
  -d '{"job_types":["Remote","Full-time"]}'
```

Valid `job_types` — casing is exact: `Full-time`, `Part-time`, `Contract`,
`Internship`, `Freelance`, `Remote`, `Hybrid`, `On-site`.

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| No CV on file | `POST /api/jobs/live-search` | **400** (not 404 — the router converts every exception to 400) |
| Missing `query` | `-d '{}'` | 422 |
| Invalid job type | `{"job_types":["remote"]}` (lowercase) | 422 |
| Non-UUID job id | `/api/jobs/details/abc` | 422 |
| Unknown job | a random UUID | 400 |

> `job_id` is typed `UUID`, but `get_job_detail` also supports JSearch external
> ids — which are not UUIDs and therefore return 422 before reaching the lookup.
> `page`/`num_pages` are unvalidated: `page=0` produces a negative offset.

---

## 5. Applications — 9 endpoints · **no authentication**

Every endpoint in this router takes `user_id` from the body or query string and
sends **no** `Authorization` header. Any caller who knows a user id can read and
modify that user's applications.

| Method | Path | `user_id` in |
|---|---|---|
| POST | `/api/application/applications/from-job` | body |
| POST | `/api/application/applications/manual` | body |
| GET | `/api/application/applications` | query |
| GET | `/api/application/applications/kanban` | query |
| PATCH | `/api/application/applications/{id}/status` | body |
| POST | `/api/application/applications/{id}/notes` | body |
| PATCH | `/api/application/notes/{note_id}` | body |
| PATCH | `/api/application/applications/{id}/archive` | query |
| DELETE | `/api/application/applications/{id}` | query |

```bash
# Track a job you found via search
curl -s -X POST "$BASE/api/application/applications/from-job" -H "$JSON" -d '{
  "user_id": "'"$USER_ID"'",
  "job": {
    "id": "'"$JOB_ID"'",
    "title": "Backend Engineer",
    "company_name": "Acme Corp",
    "location": "Dhaka, Bangladesh",
    "apply_urls": ["https://acme.example/jobs/123"]
  }
}'

# Track something you found elsewhere
curl -s -X POST "$BASE/api/application/applications/manual" -H "$JSON" -d '{
  "user_id": "'"$USER_ID"'",
  "job_title": "Platform Engineer",
  "company": "Globex",
  "location": "Remote",
  "apply_url": "https://globex.example/careers/42",
  "source": "manual",
  "salary": "$90k–$120k"
}'

export APP_ID=$(curl -s "$BASE/api/application/applications?user_id=$USER_ID" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')

curl -s "$BASE/api/application/applications?user_id=$USER_ID"
curl -s "$BASE/api/application/applications?user_id=$USER_ID&status=applied"
curl -s "$BASE/api/application/applications?user_id=$USER_ID&include_archived=true"
curl -s "$BASE/api/application/applications/kanban?user_id=$USER_ID"

curl -s -X PATCH "$BASE/api/application/applications/$APP_ID/status" -H "$JSON" \
  -d '{"user_id":"'"$USER_ID"'","status":"interviewing","reason":"Recruiter call booked"}'

curl -s -X POST "$BASE/api/application/applications/$APP_ID/notes" -H "$JSON" \
  -d '{"user_id":"'"$USER_ID"'","content":"Phone screen went well."}'

curl -s -X PATCH "$BASE/api/application/notes/$NOTE_ID" -H "$JSON" \
  -d '{"user_id":"'"$USER_ID"'","content":"Updated note."}'

curl -s -X PATCH "$BASE/api/application/applications/$APP_ID/archive?user_id=$USER_ID"
curl -s -X DELETE "$BASE/api/application/applications/$APP_ID?user_id=$USER_ID"
```

Statuses that trigger a notification: `applied`, `interviewing`, `offer`,
`rejected` (compared lowercase).

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Duplicate application | track the same job twice | 400 |
| Invalid status | `{"status":"ghosted"}` | 400 |
| Another user's application | correct id, wrong `user_id` | 404 |
| Missing `user_id` | omit it from the query | 422 |
| Non-UUID `user_id` | `?user_id=abc` | 422 |

> Try any of these with **no `Authorization` header at all** — they all succeed.
> That is the actual behaviour, not a setup mistake.

---

## 6. Chat — 14 endpoints

| Method | Path |
|---|---|
| POST | `/api/chat/message` |
| POST | `/api/chat/job/{job_id}/message` |
| GET | `/api/chat/history` |
| GET | `/api/chat/job/{job_id}/history` |
| GET | `/api/chat/sessions` |
| GET | `/api/chat/job/{job_id}/sessions` |
| POST | `/api/chat/conversations` |
| GET | `/api/chat/conversations` |
| GET | `/api/chat/conversations/{id}` |
| POST | `/api/chat/conversations/{id}/sessions` |
| GET | `/api/chat/conversations/{id}/sessions` |
| GET | `/api/chat/conversations/{id}/sessions/{sid}/messages` |
| POST | `/api/chat/conversations/{id}/sessions/{sid}/message` |
| POST | `/api/chat/conversations/{id}/summarize` |

All require auth.

```bash
# General coaching chat — conversation and session are created automatically
curl -s -X POST "$BASE/api/chat/message" -H "$AUTH" -H "$JSON" \
  -d '{"content":"What skills should I focus on next?"}'
# 200 {"content":"…","session_id":"…","conversation_id":"…","created_at":"…",
#      "tool_status":"handled","ui_payload":null,"notification":null}

# Job-scoped chat
curl -s -X POST "$BASE/api/chat/job/$JOB_ID/message" -H "$AUTH" -H "$JSON" \
  -d '{"content":"Am I a good fit for this role?"}'

curl -s "$BASE/api/chat/history?limit=20" -H "$AUTH"
curl -s "$BASE/api/chat/job/$JOB_ID/history?limit=20" -H "$AUTH"
curl -s "$BASE/api/chat/sessions" -H "$AUTH"
curl -s "$BASE/api/chat/job/$JOB_ID/sessions" -H "$AUTH"

# Explicit conversation/session management
curl -s -X POST "$BASE/api/chat/conversations" -H "$AUTH" -H "$JSON" \
  -d '{"title":"Career planning"}'                       # 201
export CONV_ID=…
curl -s "$BASE/api/chat/conversations" -H "$AUTH"
curl -s "$BASE/api/chat/conversations/$CONV_ID" -H "$AUTH"
curl -s -X POST "$BASE/api/chat/conversations/$CONV_ID/sessions" -H "$AUTH" -H "$JSON" \
  -d '{"title":"Session 1"}'                             # 201
export SESSION_ID=…
curl -s "$BASE/api/chat/conversations/$CONV_ID/sessions" -H "$AUTH"
curl -s "$BASE/api/chat/conversations/$CONV_ID/sessions/$SESSION_ID/messages" -H "$AUTH"
curl -s -X POST "$BASE/api/chat/conversations/$CONV_ID/sessions/$SESSION_ID/message" \
  -H "$AUTH" -H "$JSON" -d '{"content":"Continue where we left off."}'
curl -s -X POST "$BASE/api/chat/conversations/$CONV_ID/summarize" -H "$AUTH"
```

**Confirmation gate.** Write-capable tools pause for approval. When a reply comes
back with `tool_status: "pending_confirmation"`, send `"yes"` to proceed or
`"no"` to cancel:

```bash
curl -s -X POST "$BASE/api/chat/message" -H "$AUTH" -H "$JSON" \
  -d '{"content":"Save this job to my tracker"}'   # -> pending_confirmation
curl -s -X POST "$BASE/api/chat/message" -H "$AUTH" -H "$JSON" \
  -d '{"content":"yes"}'                           # -> executes
```

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| `limit` over the cap | `?limit=100` | 422 (`le=50`) |
| `limit` of zero or negative | `?limit=0`, `?limit=-1` | **200** — no `ge` constraint, reaches the query |
| Unknown conversation | random UUID | 404 |
| Another user's conversation | valid id, wrong owner | 404 |
| Empty content | `{"content":""}` | 200 — no `min_length` |

---

## 7. Roadmap — 6 endpoints ✅ *automated*

| Method | Path | Success | Bugs |
|---|---|---|---|
| POST | `/api/roadmap/from-conversation` | 201 | [ROADMAP-01](BUG_REPORT.md#roadmap-01), [ROADMAP-02](BUG_REPORT.md#roadmap-02) |
| POST | `/api/roadmap/from-job` | 201 | [ROADMAP-01](BUG_REPORT.md#roadmap-01), [ROADMAP-02](BUG_REPORT.md#roadmap-02) |
| POST | `/api/roadmap/manual` | 201 | |
| GET | `/api/roadmap` | 200 | [GOALS-07](BUG_REPORT.md#goals-07) |
| GET | `/api/roadmap/{id}` | 200 | |
| DELETE | `/api/roadmap/{id}` | 204 | [ROADMAP-03](BUG_REPORT.md#roadmap-03) |

```bash
# Generate from a coaching conversation
curl -s -X POST "$BASE/api/roadmap/from-conversation" -H "$AUTH" -H "$JSON" \
  -d '{"conversation_id":"'"$CONV_ID"'"}'
# 201 {"roadmap":{…phases→milestones…},"suggested_goals":[{…}]}

# Generate from a job (skill-gap analysis against your CV)
curl -s -X POST "$BASE/api/roadmap/from-job" -H "$AUTH" -H "$JSON" \
  -d '{"job_id":"'"$JOB_ID"'"}'

# Create an empty one by hand
curl -s -X POST "$BASE/api/roadmap/manual" -H "$AUTH" -H "$JSON" \
  -d '{"title":"Backend Engineer","description":"Six month plan"}'
# 201 {"id":"…","user_id":"…","title":"Backend Engineer","source_type":"manual",…}

export ROADMAP_ID=$(curl -s "$BASE/api/roadmap" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')

curl -s "$BASE/api/roadmap" -H "$AUTH"                 # list — no phases
curl -s "$BASE/api/roadmap/$ROADMAP_ID" -H "$AUTH"     # detail — nested phases+milestones
curl -s -X DELETE "$BASE/api/roadmap/$ROADMAP_ID" -H "$AUTH" -w 'HTTP %{http_code}\n'   # 204
```

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Unknown conversation | `{"conversation_id":"nope"}` | 404 `"Conversation not found"` |
| Unknown job | `{"job_id":"<random uuid>"}` | 404 `"Job not found"` |
| LLM failure | provider down | 500 `"Roadmap generation failed: …"` |
| Missing title | `POST /manual -d '{}'` | 422 |
| Unknown roadmap | random UUID | 404 |
| Another user's roadmap | valid id, wrong owner | 404 |
| Non-UUID id | `/api/roadmap/abc` | 422 |
| Trailing slash | `/api/roadmap/` | 307 |

`POST /manual` deliberately creates a roadmap with **no phases** — only the two
generate endpoints build a tree.

---

## 8. Goals — 6 endpoints ✅ *automated*

| Method | Path | Success | Bugs |
|---|---|---|---|
| POST | `/api/goals` | 201 | |
| POST | `/api/goals/from-roadmap/{roadmap_id}` | 201 | [GOALS-02](BUG_REPORT.md#goals-02), [GOALS-03](BUG_REPORT.md#goals-03) |
| GET | `/api/goals` | 200 | [GOALS-04](BUG_REPORT.md#goals-04), [GOALS-07](BUG_REPORT.md#goals-07) |
| GET | `/api/goals/{id}` | 200 | |
| PATCH | `/api/goals/{id}` | 200 | [GOALS-01](BUG_REPORT.md#goals-01), [GOALS-05](BUG_REPORT.md#goals-05) |
| DELETE | `/api/goals/{id}` | 204 | |

```bash
# Create a standalone goal
curl -s -X POST "$BASE/api/goals" -H "$AUTH" -H "$JSON" -d '{
  "title": "Finish the SQL course",
  "description": "Complete all modules and the capstone",
  "target_date": "2026-12-31"
}'
# 201 {"id":"…","status":"not_started","source_type":"manual","roadmap_id":null,…}

# Promote every milestone of a roadmap
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH"
# 201 [{…}, {…}, {…}]   — target dates stack cumulatively

# Promote only selected milestones
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" -H "$JSON" \
  -d '{"milestone_ids":["<milestone-uuid-1>","<milestone-uuid-2>"]}'

export GOAL_ID=$(curl -s "$BASE/api/goals" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')

curl -s "$BASE/api/goals" -H "$AUTH"
curl -s "$BASE/api/goals?status=in_progress" -H "$AUTH"
curl -s "$BASE/api/goals/$GOAL_ID" -H "$AUTH"

curl -s -X PATCH "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -H "$JSON" \
  -d '{"status":"completed"}'                          # fires a notification

curl -s -X DELETE "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -w 'HTTP %{http_code}\n'   # 204
```

Valid statuses: `not_started`, `in_progress`, `completed`, `paused`.

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Missing title | `-d '{"description":"x"}'` | 422 |
| Malformed date | `"target_date":"31-12-2026"` | 422 |
| Invalid status filter | `?status=done` | **400** (not 422 — validated in the route) |
| Invalid status on PATCH | `{"status":"finished"}` | 400 |
| Empty PATCH body | `-d '{}'` | 200, unchanged |
| Clearing a field | `{"target_date":null}` | 200 but **not cleared** — [GOALS-01](BUG_REPORT.md#goals-01) |
| Unknown roadmap | random UUID | 404 |
| Unknown milestone ids | `{"milestone_ids":["nope"]}` | **201 `[]`** — [GOALS-03](BUG_REPORT.md#goals-03) |
| Promoting twice | repeat the same POST | duplicates every goal — [GOALS-02](BUG_REPORT.md#goals-02) |

---

## 9. Notifications — 4 REST + 1 WebSocket ✅ *automated*

| Method | Path | Success | Bugs |
|---|---|---|---|
| GET | `/api/notifications` | 200 | [NOTIF-01](BUG_REPORT.md#notif-01), [NOTIF-05](BUG_REPORT.md#notif-05) |
| PATCH | `/api/notifications/{id}/read` | 200 | |
| POST | `/api/notifications/mark-all-read` | 200 | [NOTIF-02](BUG_REPORT.md#notif-02) |
| DELETE | `/api/notifications/{id}` | 204 | |
| WS | `/ws/notifications` | — | [NOTIF-03](BUG_REPORT.md#notif-03), [NOTIF-04](BUG_REPORT.md#notif-04) |

```bash
curl -s "$BASE/api/notifications" -H "$AUTH"
curl -s "$BASE/api/notifications?unread_only=true" -H "$AUTH"

export NOTIF_ID=$(curl -s "$BASE/api/notifications" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')

curl -s -X PATCH "$BASE/api/notifications/$NOTIF_ID/read" -H "$AUTH"
curl -s -X POST "$BASE/api/notifications/mark-all-read" -H "$AUTH"
# {"marked_read":3}
curl -s -X DELETE "$BASE/api/notifications/$NOTIF_ID" -H "$AUTH" -w 'HTTP %{http_code}\n'   # 204
```

**WebSocket** — note it is mounted at the **root**, not under `/api`, and the
token goes in the **query string**:

```bash
# npm i -g wscat
wscat -c "ws://localhost:8000/ws/notifications?token=$TOKEN"
```

On connect the server immediately pushes every unread notification as individual
JSON frames, then holds the connection open. Frames look like:

```json
{"id":"…","type":"goal_completed","title":"Goal completed!",
 "message":"You completed \"Finish the SQL course\". Keep up the momentum!",
 "data":{"goal_id":"…"},"is_read":false,"created_at":"2026-07-30T10:00:00"}
```

Note the WS frame omits `user_id`, which the REST shape includes.

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| No token | `wscat -c ".../ws/notifications"` | close code **4001** "Missing token" |
| Invalid token | `?token=garbage` | close **4001** "Auth failed" |
| Unknown notification | random UUID | 404 |
| Another user's notification | valid id, wrong owner | 404 |
| Nothing unread | `POST /mark-all-read` | 200 `{"marked_read":0}` |
| Many notifications | 250 in the inbox | all 250 returned — [NOTIF-01](BUG_REPORT.md#notif-01) |

**Notification types produced by the system:** `cv_parsed`, `cv_activated`,
`application_saved`, `application_status_changed`, `goals_created_from_roadmap`,
`goal_completed`, `roadmap_generated`.

---

## 10. Cover Letter — 5 endpoints

| Method | Path | Success |
|---|---|---|
| POST | `/api/cover-letter/generate` | 200 |
| GET | `/api/cover-letter/` | 200 |
| GET | `/api/cover-letter/{id}` | 200 |
| PATCH | `/api/cover-letter/{id}` | 200 |
| DELETE | `/api/cover-letter/{id}` | 204 |

```bash
curl -s -X POST "$BASE/api/cover-letter/generate" -H "$AUTH" -H "$JSON" \
  -d '{"job_id":"'"$JOB_ID"'","tone":"professional"}'

# NOTE the trailing slash here — this router is the odd one out
curl -s "$BASE/api/cover-letter/" -H "$AUTH"

export CL_ID=$(curl -s "$BASE/api/cover-letter/" -H "$AUTH" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')

curl -s "$BASE/api/cover-letter/$CL_ID" -H "$AUTH"
curl -s -X PATCH "$BASE/api/cover-letter/$CL_ID" -H "$AUTH" -H "$JSON" \
  -d '{"content":"My edited cover letter text."}'
curl -s -X DELETE "$BASE/api/cover-letter/$CL_ID" -H "$AUTH" -w 'HTTP %{http_code}\n'   # 204
```

Tones: `professional`, `enthusiastic`, `concise`. An unrecognised tone silently
falls back to `professional` — but the string you sent is what gets stored.

**Edge cases**

| Case | Request | Expect |
|---|---|---|
| Unknown job | `{"job_id":"<random>"}` | 404 |
| Missing `job_id` | `-d '{}'` | 422 |
| Unknown cover letter | random id | 404 |
| No trailing slash | `GET /api/cover-letter` | 307 |
| Arbitrary id string | `/api/cover-letter/abc` | 404, **not** 422 (id is a plain `str`) |

---

## Full smoke run

End-to-end pass over the main journey. Each step assumes the previous succeeded.

```bash
set -e
export BASE=http://localhost:8000

curl -sf "$BASE/health" | grep -q healthy && echo "✓ health"

export TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"tester@example.com","password":"Sup3rSecret!"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
export AUTH="Authorization: Bearer $TOKEN"
export JSON="Content-Type: application/json"
echo "✓ login"

export USER_ID=$(curl -s "$BASE/api/auth/me" -H "$AUTH" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "✓ me: $USER_ID"

curl -s -X POST "$BASE/api/cv/upload-cv" -H "$AUTH" -F "file=@resume.pdf" >/dev/null && echo "✓ cv upload"
curl -s "$BASE/api/jobs/suggest-from-my-cv" -H "$AUTH" >/dev/null && echo "✓ suggestions"

export ROADMAP_ID=$(curl -s -X POST "$BASE/api/roadmap/manual" -H "$AUTH" -H "$JSON" \
  -d '{"title":"Smoke test roadmap"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "✓ roadmap: $ROADMAP_ID"

curl -s -X POST "$BASE/api/goals" -H "$AUTH" -H "$JSON" -d '{"title":"Smoke goal"}' >/dev/null && echo "✓ goal"
curl -s "$BASE/api/notifications" -H "$AUTH" >/dev/null && echo "✓ notifications"

curl -s -X DELETE "$BASE/api/roadmap/$ROADMAP_ID" -H "$AUTH" -o /dev/null -w '✓ cleanup (%{http_code})\n'
```

---

## Endpoint count

| Router | Endpoints | Auth | Automated |
|---|---|---|---|
| System | 2 | no | — |
| Authentication | 4 | 1 of 4 | — |
| CV | 4 | yes | — |
| Jobs | 9 | yes | — |
| Applications | 9 | **none** | — |
| Chat | 14 | yes | — |
| Roadmap | 6 | yes | ✅ 37 tests |
| Goals | 6 | yes | ✅ 51 tests |
| Notifications | 4 + 1 WS | yes | ✅ 53 tests |
| Cover Letter | 5 | yes | — |
| **Total** | **63 HTTP + 1 WS** | | **197 tests** |
