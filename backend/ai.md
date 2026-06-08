# CareerPilot — AI Assistant Guide

Base URL: `http://localhost:8000` | Swagger: `http://localhost:8000/docs`

---

## How the AI Assistant Works

The assistant is a career coach named Praxis. It runs on every `/api/chat/*` endpoint and has two modes:

### Mode 1 — General Coaching (`POST /api/chat/message`)
- Grounded in your CV (fetched from DB, injected into every message)
- Has memory of past sessions (summaries carried across conversations)
- Good for: career advice, interview prep, skill gap analysis, general questions

### Mode 2 — Job-Specific Coaching (`POST /api/chat/job/{job_id}/message`)
- Everything from Mode 1 PLUS the specific job context + your fit score for that job
- Good for: "should I apply?", "what to highlight?", "what am I missing for this role?"

---

## AI Context Pipeline (what the AI sees every message)

```
Your CV (from DB)
  + Last session summary (cross-session memory)
  + [Job context + fit score] (only in job mode)
  + Last 10 messages from current session
  + System rules (tool confirmation rules, response format)
  + Your new message
→ Sent to LLM (Groq llama-3.3-70b-versatile)
→ AI may call tools or reply directly
→ Response saved to DB, returned to you
```

---

## Tool Confirmation Rules

| Tool | Type | Confirmed before calling? |
|------|------|--------------------------|
| `search_jobs` | Read | ✅ AI describes + asks first |
| `get_fit_score` | Read | ✅ AI describes + asks first |
| `get_my_applications` | Read | ✅ AI describes + asks first |
| `get_my_goals` | Read | ✅ AI describes + asks first |
| `save_to_tracker` | Write | ✅ AI describes + asks first |
| `generate_roadmap` | Write | ✅ AI describes + asks first |
| `draft_cover_letter` | Write | ✅ AI describes + asks first |
| `create_goals` | Write | ✅ AI describes + asks first |

Every tool — read or write — requires explicit user confirmation before it executes.

If you ask "find me jobs" → AI says "I'll search for jobs in X — shall I go ahead?" → waits for yes.
If you ask "save this job" → AI says "I'll save X to your tracker, shall I?" → waits for yes.

---

## Chat Endpoints

### `POST /api/chat/message`
General coaching. Auth required.
```json
{ "content": "What skills do I need to become a senior backend engineer?" }
```
**Response:**
```json
{
  "content": "Based on your CV...",
  "session_id": "uuid",
  "conversation_id": "uuid",
  "created_at": "2026-06-08T..."
}
```

---

### `POST /api/chat/job/{job_id}/message`
Job-scoped coaching. Use a `job_id` from `GET /api/jobs/details/{id}` or live search.
```json
{ "content": "Am I a good fit? What should I highlight?" }
```
The AI sees the job title, company, required skills, your fit score, and your matched/missing skills.

---

### `GET /api/chat/history`
Returns last 20 messages from your general chat (newest first).
Optional: `?limit=10&before={message_id}` for pagination.

---

### `GET /api/chat/job/{job_id}/history`
Returns message history for a job-specific conversation.

---

### `GET /api/chat/sessions`
Lists past coaching sessions with their summaries.
Sessions auto-rotate after 15 messages — the old session is summarized and its key points carry forward as memory.

---

### `GET /api/chat/job/{job_id}/sessions`
Lists past sessions for a job-specific chat.

---

## How to Test the Assistant Is Working Correctly

### Step 1 — Prerequisites
Make sure you have a CV uploaded (`POST /api/cv/upload-cv`) and at least one job detail fetched (`GET /api/jobs/details/{id}`).

### Step 2 — Test general coaching (CV grounded)
`POST /api/chat/message`
```json
{ "content": "What are my strongest skills based on my CV?" }
```
**Pass criteria:**
- Response mentions your actual skills from the CV (e.g., "Python", "FastAPI" — whatever is in your resume)
- Does NOT give generic advice like "Consider learning programming"
- `content` field is non-empty

### Step 3 — Test job coaching (job context grounded)
Take a real `job_id` from `GET /api/jobs/details/{id}`.
`POST /api/chat/job/{job_id}/message`
```json
{ "content": "Am I a good fit for this role?" }
```
**Pass criteria:**
- Response mentions the specific job title and company
- References your matched strengths AND missing skills
- Gives a percentage estimate or verdict (e.g., "You're a 72% match...")

### Step 4 — Test tool confirmation (write tool)
`POST /api/chat/message`
```json
{ "content": "Create a career roadmap for me" }
```
**Pass criteria:**
- AI describes what the roadmap will contain
- AI ASKS for your confirmation ("Shall I create this?", "Would you like me to proceed?")
- Does NOT create the roadmap immediately

### Step 5 — Confirm (test write tool executes after confirmation)
`POST /api/chat/message`
```json
{ "content": "Yes, go ahead" }
```
**Pass criteria:**
- AI calls `generate_roadmap` tool
- Returns confirmation that roadmap was created with an ID
- `GET /api/roadmap` shows the new roadmap

### Step 6 — Test read tool (no confirmation)
`POST /api/chat/message`
```json
{ "content": "Show me my current job applications" }
```
**Pass criteria:**
- AI immediately lists your applications without asking first
- If you have no applications: "You have no active job applications yet."

### Step 7 — Test session memory
Send 3+ messages in general chat, then:
`GET /api/chat/sessions`
**Pass criteria:**
- Sessions list shows at least one entry
- After 15 messages, a new session starts automatically and the old one gets a summary

### Step 8 — Test history pagination
`GET /api/chat/history?limit=5`
**Pass criteria:**
- Returns exactly 5 messages (or fewer if you have fewer)
- Messages alternate between `role: user` and `role: assistant`

---

## What "Correct" Looks Like

| Test | Correct | Incorrect |
|------|---------|-----------|
| CV grounded | Mentions your actual job titles/skills | "You should learn to code" |
| Job grounded | Names the company and role | Generic interview tips |
| Write tool | Asks before acting | Creates roadmap instantly |
| Read tool | Acts instantly | Asks "shall I search?" |
| Fit score in chat | Shows percentage + matched/missing | "I don't know your fit" |
| Session memory | Recalls topics from last session | Treats every chat as fresh |

---

## Session Rotation (automatic)

Every 15 messages, the current session is:
1. Summarized by LLM into 3–4 bullet points (key insights, gaps, advice)
2. Summary saved to DB
3. New session starts
4. Old summary injected into future messages as memory

This means the AI remembers what you discussed even across sessions.

---

## Known Behavior

- **Tool use failure (400)**: Fixed. `parallel_tool_calls: false` is now always set in the API payload when tools are used, preventing Groq from generating XML-format tool calls. A fallback retry without tools is also in place for any remaining 400 errors.
- **fit_score null in search results**: Fit score is computed at job detail time, not during search. Open a job's detail view to get the score.
- **Live job IDs**: Jobs from live search have temporary UUIDs (2h TTL in Redis). Once you open the detail view, the job is saved permanently to DB with that UUID.
- **Job coaching requires fetching detail first**: Call `GET /api/jobs/details/{id}` before `POST /api/chat/job/{id}/message` so the job exists in DB with a fit score.
