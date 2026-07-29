# Bug Report — HTTP layer: goals · notifications · roadmap

**Status:** in progress — `goals` and `roadmap` complete, `notifications` pending.
**Scope:** the route / schema / model layer of the goals, notifications, and roadmap modules.
**Bugs are reproduced and documented here, not fixed.**

Every bug below has an automated reproduction in `tests/` marked
`@pytest.mark.bug`. Each asserts the behaviour the code **should** have and
carries `xfail(strict=True)`, so a run reports them as `xfailed` rather than
passing:

```bash
make test-bugs            # 22 xfailed — one per reproduction below
make test                 # 175 passed, 22 xfailed
```

`strict=True` means that **fixing a bug turns its test into an `XPASS`, which
fails the build**. That is the signal to remove the `xfail` marker and mark the
entry resolved here — a fix can't quietly leave a stale test behind.

Ids are prefixed by module: `GOALS-` here, with `ROADMAP-` and `NOTIF-` added as
those suites are written.

| ID | Severity | Module | Summary |
|---|---|---|---|
| [GOALS-01](#goals-01) | High | goals | `description` / `target_date` can never be cleared |
| [GOALS-02](#goals-02) | High | goals | Promoting a roadmap twice duplicates every goal |
| [GOALS-03](#goals-03) | Medium | goals | Unknown `milestone_ids` silently ignored, returns `201 []` |
| [GOALS-04](#goals-04) | Low | goals | Validation message order changes between restarts |
| [GOALS-05](#goals-05) | Low | goals | Re-completing a goal re-sends the notification |
| [GOALS-06](#goals-06) | Low | goals | Debug `print()` writes user ids to stdout |
| [GOALS-07](#goals-07) | Low | goals | `/api/goals/` 307-redirects; API inconsistent with cover-letter |
| [ROADMAP-01](#roadmap-01) | Medium | roadmap | `HTTPException` from the service is re-reported as 500 (latent) |
| [ROADMAP-02](#roadmap-02) | Low | roadmap | Generate endpoints declare no `response_model` |
| [ROADMAP-03](#roadmap-03) | High | roadmap · goals | Deleting a roadmap orphans its goals into a contradictory state |
| [NOTIF-01](#notif-01) | Medium | notifications | Inbox is unbounded — no limit, offset, or cursor |
| [NOTIF-02](#notif-02) | Low | notifications | `mark-all-read` declares no `response_model` |
| [NOTIF-03](#notif-03) | Medium | notifications | WebSocket auth token travels in the query string |
| [NOTIF-04](#notif-04) | Medium | notifications | One failing row silently drops every later notification |
| [NOTIF-05](#notif-05) | Medium | notifications | A NULL `created_at` makes the whole inbox return 500 |

Two further candidates were investigated and found **not** to be reportable bugs
— see [Investigated and dismissed](#investigated-and-dismissed).

Setup shared by every curl example:

```bash
BASE=http://localhost:8000
TOKEN=<a valid Supabase access token>
AUTH="Authorization: Bearer $TOKEN"
```

---

## GOALS-01

**`description` and `target_date` can never be cleared once set** · **High**

`backend/app/modules/goals/route.py:114`, `backend/app/modules/goals/db_service.py:110`

### Description

`update_goal` builds its update payload with `exclude_none=True`:

```python
data = body.model_dump(exclude_none=True)
```

`GoalUpdate` declares every field `Optional[... ] = None`, so this cannot
distinguish *"the client omitted this field"* from *"the client explicitly sent
`null` to clear it"*. Both vanish before reaching the db layer, which then
iterates only over the keys that survived.

The API returns `200 OK` with the unchanged value, so the client believes the
write succeeded. There is no other endpoint that can clear these fields, making
a set `target_date` permanent for the life of the goal.

`exclude_unset=True` is the correct switch here — it keeps explicit `null`s and
drops only genuinely absent keys.

### Reproduction

```bash
# Create a goal with a deadline
GOAL=$(curl -s -X POST "$BASE/api/goals" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"Ship v1","description":"Cut the release","target_date":"2026-12-31"}')
GOAL_ID=$(echo "$GOAL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

# Try to clear both fields
curl -s -X PATCH "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"target_date":null,"description":null}'
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_target_date_cannot_be_cleared
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_description_cannot_be_cleared
```

**Expected:** `200` with `"target_date": null, "description": null`.
**Actual:** `200` with `"target_date": "2026-12-31", "description": "Cut the release"` — silently unchanged.

### Suggested fix (not applied)

Use `body.model_dump(exclude_unset=True)` in `route.py:114`.

---

## GOALS-02

**`POST /goals/from-roadmap/{id}` is not idempotent — every call duplicates the whole goal set** · **High**

`backend/app/modules/goals/route.py:37`, `backend/app/modules/goals/db_service.py:38`

### Description

`create_goals_from_milestones` unconditionally constructs a new `Goal` per
milestone. Nothing checks whether a goal already exists for
`(user_id, milestone_id)`, and there is no unique constraint on the table.

A user who taps "add to my goals" twice — or a client that retries a request
that actually succeeded — silently doubles their tracker. Each duplicate is a
distinct row with its own id, so there is no way to tell them apart or
de-duplicate after the fact. The accompanying notification fires again too,
reporting the full count each time.

This is reachable by ordinary double-clicking, not just by a malicious caller.

### Reproduction

```bash
# ROADMAP_ID must be a roadmap owned by $TOKEN's user, with milestones
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)),"goals")'
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)),"goals")'
curl -s "$BASE/api/goals" -H "$AUTH" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)),"total")'
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_promoting_a_roadmap_twice_duplicates_every_goal
```

**Expected:** second call is a no-op (or `409`); total stays at N.
**Actual:** `201` both times; total is 2N. With a 3-milestone roadmap: 3, then 3, total 6.

### Suggested fix (not applied)

Skip milestones that already have a goal for this user, and add a unique
constraint on `(user_id, milestone_id)` where `milestone_id IS NOT NULL`.

---

## GOALS-03

**Unknown or cross-roadmap `milestone_ids` are silently discarded** · **Medium**

`backend/app/modules/goals/db_service.py:50-52`

### Description

```python
requested_set = set(milestone_ids)
milestones_to_use = [m for m in all_milestones if m.id in requested_set]
```

Requested ids that match nothing in the roadmap are dropped without comment.
The endpoint returns `201 Created` with an empty (or short) list, which is the
same response shape as a legitimately empty roadmap.

Two ways to hit this: a stale client sending milestone ids from a roadmap that
has since been regenerated, and a client accidentally sending ids belonging to a
*different* roadmap. In both cases the caller is told the operation succeeded.

Compounding it, `201 Created` is returned even when nothing was created.

### Reproduction

```bash
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"milestone_ids":["does-not-exist"]}' -w '\nHTTP %{http_code}\n'
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_unknown_milestone_ids_are_silently_ignored
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_milestones_from_another_roadmap_are_silently_ignored
```

**Expected:** `400`/`404` naming the unresolvable ids.
**Actual:** `HTTP 201` with body `[]`.

### Suggested fix (not applied)

Diff `requested_set` against the resolved milestone ids and raise `400` listing
the leftovers.

---

## GOALS-04

**Validation error message re-orders itself between server restarts** · **Low**

`backend/app/modules/goals/route.py:87`, `:119`

### Description

`_VALID_STATUSES` is a `set`, and both error paths render it directly:

```python
detail=f"Invalid status. Must be one of: {', '.join(_VALID_STATUSES)}"
```

Python randomizes string hashing per process (`PYTHONHASHSEED`), so set
iteration order differs on every boot. Five consecutive interpreter runs produce
five different orderings:

```
not_started, completed, in_progress, paused
paused, not_started, in_progress, completed
not_started, paused, in_progress, completed
not_started, in_progress, paused, completed
in_progress, paused, completed, not_started
```

The message is part of the public API contract. Clients cannot string-match it,
docs and snapshot tests go stale at random, and identical deployments return
different bodies for the same request.

### Reproduction

```bash
curl -s "$BASE/api/goals?status=bogus" -H "$AUTH"
# restart the server, repeat — the order of the four statuses changes
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_invalid_status_message_has_unstable_ordering
```

**Expected:** a stable, documented ordering.
**Actual:** arbitrary per-process ordering.

### Suggested fix (not applied)

Make the statuses an ordered `tuple` (or a `str, Enum`) and let FastAPI reject
invalid values as `422` at the schema layer instead of hand-rolling `400`s.

---

## GOALS-05

**Re-sending `completed` re-notifies every time** · **Low**

`backend/app/modules/goals/route.py:125`

### Description

```python
if data.get("status") == "completed":
    background_tasks.add_task(notify, ...)
```

The notification is gated on what the *request asked for*, not on whether a
transition actually occurred. The prior status is never consulted, so a goal
that is already `completed` fires "Goal completed!" again on every PATCH.

Any client that PATCHes the full goal object on save — a common pattern — will
re-notify on every edit to an already-completed goal.

### Reproduction

```bash
curl -s -X PATCH "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -H 'Content-Type: application/json' -d '{"status":"completed"}' >/dev/null
curl -s -X PATCH "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -H 'Content-Type: application/json' -d '{"status":"completed"}' >/dev/null
curl -s -X PATCH "$BASE/api/goals/$GOAL_ID" -H "$AUTH" -H 'Content-Type: application/json' -d '{"status":"completed"}' >/dev/null

curl -s "$BASE/api/notifications" -H "$AUTH" | python3 -c 'import json,sys; print(sum(n["type"]=="goal_completed" for n in json.load(sys.stdin)),"notifications")'
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_recompleting_a_goal_fires_a_duplicate_notification
```

**Expected:** 1 notification.
**Actual:** 3 — one per request.

### Suggested fix (not applied)

Capture the status before the update and notify only on
`previous != "completed" and new == "completed"`.

---

## GOALS-06

**Debug `print()` statements write user ids and roadmap contents to stdout** · **Low**

`backend/app/modules/goals/route.py:48,51,63` · `backend/app/modules/goals/db_service.py:46,48,56`
· `backend/app/modules/roadmap/db_service.py:89,98`

### Description

The milestone-promotion path is instrumented with leftover debug prints. One
request emits:

```
[goals/from-roadmap] roadmap_id='d1a15d03-…'  user_id='22222222-2222-4222-8222-222222222222'
[goals/from-roadmap] roadmap lookup → <app.modules.roadmap.models.Roadmap object at 0x…>
[get_all_milestones_for_roadmap] roadmap_id='d1a15d03-…'  phases in DB=1
[get_all_milestones_for_roadmap] milestone rows returned=3
[create_goals_from_milestones] roadmap_id='d1a15d03-…'  milestones found=3
  milestone id='132ee089-…'  title='Learn SQL joins'
  milestone id='15206541-…'  title='Build a REST API'
  milestone id='fdd5259b-…'  title='Ship to prod'
[create_goals_from_milestones] milestones_to_use=3
[goals/from-roadmap] goals created → 3
```

That is ~10 lines per request containing user ids and the user's career-plan
contents, going to stdout — captured by the platform log collector, outside any
log-level control, and not redactable.

### Reproduction

```bash
# Watch the server's stdout while running:
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" >/dev/null
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_debug_prints_leak_user_ids_to_stdout
```

**Expected:** no per-request stdout output; diagnostics behind `logger.debug`.
**Actual:** ~10 lines per request including the user id and every milestone title.

### Suggested fix (not applied)

Delete the prints, or move them to a module `logger` at `DEBUG` with ids omitted.

---

## GOALS-07

**`/api/goals/` 307-redirects, and the convention is inconsistent across modules** · **Low**

`backend/app/modules/goals/route.py:20,75` · `backend/app/modules/roadmap/route.py:92`
· `backend/app/modules/notifications/route.py:20` · `backend/app/modules/cover_letter/route.py:50`

### Description

Goals, roadmap, and notifications register their collection routes as `""`,
producing `/api/goals` with no trailing slash. Requests to `/api/goals/` get a
`307 Temporary Redirect` instead of the resource.

`cover_letter` registers `"/"` instead, so it behaves the *opposite* way —
`/api/cover-letter/` is canonical and `/api/cover-letter` redirects. A client
cannot apply one trailing-slash convention across the API.

The redirect also means a `POST` body is replayed to the redirect target, which
some HTTP clients decline to follow, and any `Authorization` header is dropped
by clients that treat the redirect as cross-origin.

### Reproduction

```bash
curl -s -o /dev/null -w 'goals no-slash:   %{http_code}\n' "$BASE/api/goals" -H "$AUTH"
curl -s -o /dev/null -w 'goals slash:      %{http_code}\n' "$BASE/api/goals/" -H "$AUTH"
curl -s -o /dev/null -w 'cover-letter:     %{http_code}\n' "$BASE/api/cover-letter" -H "$AUTH"
curl -s -o /dev/null -w 'cover-letter /:   %{http_code}\n' "$BASE/api/cover-letter/" -H "$AUTH"
```

```
pytest tests/api/test_goals_routes.py::TestKnownBugs::test_trailing_slash_redirects_instead_of_serving
```

**Expected:** one consistent convention across all routers.
**Actual:** `/api/goals/` → `307`; `/api/cover-letter` → `307`. Opposite directions.

### Suggested fix (not applied)

Standardise on `""` everywhere (change `cover_letter/route.py:50`), and document
the no-trailing-slash convention.

---

## ROADMAP-01

**`HTTPException` raised inside the service is re-reported as 500** · **Medium** · *latent*

`backend/app/modules/roadmap/route.py:36`, `:61`

### Description

Both generate endpoints wrap their service call like this:

```python
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {str(e)}")
```

`HTTPException` is a subclass of `Exception`, so the second handler catches it
too. Any deliberate status a dependency raises — 401, 403, 404 — is discarded and
replaced with 500, with the original status left only as text inside `detail`.
The client sees a server fault where the truth was an auth or not-found problem.

**Currently latent.** No code reachable from `generate_from_conversation` or
`generate_from_job` raises `HTTPException` today — `fetch_resume_from_db` does,
but `generate_from_job:122-125` already swallows it in its own `try/except`. The
handler is nonetheless wrong and will mask the status the moment any dependency
starts raising one. Reported because the fix is one line and the failure mode is
silent.

Note the correct pattern is already used elsewhere in this codebase — e.g.
`goals/route.py` re-raises `HTTPException` before its generic handler.

### Reproduction

The service must raise an `HTTPException` for this to surface, which no current
path does — so the reproduction patches one in:

```
pytest tests/api/test_roadmap_routes.py::TestKnownBugs::test_an_http_exception_from_the_service_becomes_a_500
```

**Expected:** the service's own status code propagates (403 in the test).
**Actual:** `500`, detail `"Roadmap generation failed: 403: CV belongs to another user"`.

### Suggested fix (not applied)

Add `except HTTPException: raise` above the generic handler in both endpoints.

---

## ROADMAP-02

**Generate endpoints declare no `response_model`** · **Low**

`backend/app/modules/roadmap/route.py:24`, `:49`

### Description

```python
@router.post("/from-conversation", status_code=201)
@router.post("/from-job", status_code=201)
```

Both return `roadmap_service.build_roadmap_insight_preview(roadmap)` — a plain
dict. The schema that describes it, `RoadmapInsightPreview`
(`roadmap/schemas.py:86`), exists and even carries a docstring explaining the
contract, but is never attached to either route.

Consequences: the response is never validated, so a change to
`build_roadmap_insight_preview` can silently alter the API; and OpenAPI documents
the 201 body as an empty schema `{}`, so generated clients get an untyped
response for the two most complex payloads in the module.

Every other roadmap endpoint sets `response_model` — these two are the outliers.

### Reproduction

```bash
curl -s "$BASE/openapi.json" \
  | python3 -c 'import json,sys; s=json.load(sys.stdin); print(s["paths"]["/api/roadmap/from-job"]["post"]["responses"]["201"]["content"]["application/json"]["schema"])'
```

```
pytest tests/api/test_roadmap_routes.py::TestKnownBugs::test_generate_endpoints_have_no_response_model
```

**Expected:** the 201 schema references `RoadmapInsightPreview`.
**Actual:** `{}` — any shape accepted, nothing documented.

### Suggested fix (not applied)

Add `response_model=RoadmapInsightPreview` to both decorators.

---

## ROADMAP-03

**Deleting a roadmap orphans its goals into a self-contradictory state** · **High**

`backend/app/modules/roadmap/models.py:27-33`, `backend/app/modules/goals/models.py:26-31`,
`backend/app/modules/roadmap/db_service.py:76-82`

### Description

`Roadmap` declares two child relationships with different cascade rules:

```python
phases = relationship("RoadmapPhase", cascade="all, delete-orphan", ...)   # models.py:27
goals  = relationship("Goal", back_populates="roadmap")                    # models.py:33 — no cascade
```

Deleting a roadmap therefore destroys every phase and milestone, but leaves the
goals behind with `roadmap_id` and `milestone_id` nulled by SQLAlchemy's default
behaviour. `source_type` is never touched.

The result is a row that contradicts itself:

```json
{ "title": "Learn SQL", "source_type": "roadmap", "roadmap_id": null, "milestone_id": null }
```

It claims to originate from a roadmap while being unable to name one, and the
milestone that defined it no longer exists. A client rendering "from your
roadmap" has nothing to link to.

Three consequences, each with a test:

1. **The goals silently outlive their source.** Nothing warns the user that
   deleting a roadmap will leave orphans behind.
2. **There is no recovery path.** Rebuilding the roadmap mints new milestone
   ids, so re-promoting creates a *second* set of goals rather than reattaching
   the orphans — compounding [GOALS-02](#goals-02). The user is left with
   duplicate titles to clean up by hand.
3. **Completed work becomes unattributable.** A goal already marked `completed`
   keeps its status but loses every reference to the roadmap it belonged to, so
   the roadmap's completion history cannot be reconstructed.

Note the parallel `milestone` relationship on `Goal` has the same gap, and the
`ondelete="SET NULL"` clauses on both FKs only apply at the database level — the
ORM nulls them first regardless.

### Reproduction

```bash
# promote a roadmap's milestones to goals
curl -s -X POST "$BASE/api/goals/from-roadmap/$ROADMAP_ID" -H "$AUTH" >/dev/null

# delete the roadmap
curl -s -X DELETE "$BASE/api/roadmap/$ROADMAP_ID" -H "$AUTH" -w 'HTTP %{http_code}\n'

# the goals are still there, now unattributable
curl -s "$BASE/api/goals" -H "$AUTH" \
  | python3 -c 'import json,sys; [print(g["title"], g["source_type"], g["roadmap_id"]) for g in json.load(sys.stdin)]'
# Learn SQL   roadmap   None
```

```
pytest tests/flows/test_roadmap_to_goals_flow.py::TestKnownBugs -v
```

**Expected:** one of — cascade-delete the goals, block the delete while goals
exist, or rewrite `source_type` to `"manual"` so the row stays self-consistent.
**Actual:** orphaned goals claiming an origin they cannot name.

### Suggested fix (not applied)

Decide the intended semantics and encode it. If goals should survive (defensible
— they represent the user's own work), then set `source_type = "manual"` and copy
the roadmap title into `description` during deletion, so no row is left
self-contradictory. If they should not, add
`cascade="all, delete-orphan"` to `Roadmap.goals`.

---

## NOTIF-01

**The notification inbox is unbounded** · **Medium**

`backend/app/modules/notifications/route.py:20`, `backend/app/modules/notifications/db_service.py:26`

### Description

```python
@router.get("", response_model=list[NotificationOut])
def list_notifications(unread_only: bool = Query(default=False), ...):
    return notif_db.get_notifications(db, str(current_user.id), unread_only=unread_only)
```

`unread_only` is the only parameter. There is no `limit`, `offset`, `page`, or
cursor, and `get_notifications` applies no `.limit()` — it returns every row the
user has ever accumulated, ordered by `created_at DESC`.

Notifications are generated by ordinary activity: CV upload, every goal completion,
every roadmap generation, every application status change, every roadmap→goals
promotion. There is no expiry job and no cap, so this grows without bound for
active users. Both the SQL result set and the serialised JSON scale linearly, and
the WebSocket connect handler (`route.py:85`) replays the same unbounded query as
individual frames on every connect.

A client that only ever wants "the latest 20 for the bell icon" has no way to ask
for that.

### Reproduction

```bash
# after generating a few hundred notifications through normal use
curl -s "$BASE/api/notifications" -H "$AUTH" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)),"returned")'

# and confirm no pagination parameter exists
curl -s "$BASE/openapi.json" \
  | python3 -c 'import json,sys; s=json.load(sys.stdin); print([p["name"] for p in s["paths"]["/api/notifications"]["get"]["parameters"]])'
```

```
pytest tests/api/test_notifications_routes.py::TestKnownBugs::test_the_inbox_is_unbounded
pytest tests/api/test_notifications_routes.py::TestKnownBugs::test_no_pagination_parameters_are_offered
```

**Expected:** a default page size (e.g. 20) with `limit`/`before` parameters — the
chat module already does exactly this at `chat/route.py:70`.
**Actual:** all 250 seeded rows returned; `['unread_only']` is the complete
parameter list.

### Suggested fix (not applied)

Add `limit: int = Query(20, ge=1, le=100)` and a `before` cursor, mirroring
`chat/route.py:70`, and apply `.limit()` in `get_notifications`.

---

## NOTIF-02

**`mark-all-read` declares no `response_model`** · **Low**

`backend/app/modules/notifications/route.py:41`

### Description

```python
@router.post("/mark-all-read")
def mark_all_notifications_read(...):
    return {"marked_read": count}
```

The other three notification endpoints all declare `response_model`; this one
returns a bare dict. The `{"marked_read": int}` contract is therefore neither
validated on the way out nor present in the OpenAPI schema, which documents the
200 body as `{}`. Generated clients get an untyped response.

Same class of defect as [ROADMAP-02](#roadmap-02).

### Reproduction

```bash
curl -s "$BASE/openapi.json" \
  | python3 -c 'import json,sys; s=json.load(sys.stdin); print(s["paths"]["/api/notifications/mark-all-read"]["post"]["responses"]["200"]["content"]["application/json"]["schema"])'
```

```
pytest tests/api/test_notifications_routes.py::TestKnownBugs::test_mark_all_read_has_no_response_model
```

**Expected:** a declared schema with `marked_read: int`.
**Actual:** `{}`.

### Suggested fix (not applied)

Add a `MarkAllReadOut` model to `notifications/schemas.py` and attach it.

---

## NOTIF-03

**WebSocket auth token travels in the query string** · **Medium**

`backend/app/modules/notifications/route.py:63`

### Description

```python
async def ws_notifications(websocket: WebSocket, token: Optional[str] = Query(default=None)):
```

The Supabase **access token** — the same bearer credential the REST endpoints
take in an `Authorization` header — is accepted as a URL query parameter. URLs
are logged in places request headers are not:

- reverse-proxy and load-balancer access logs (nginx logs the full request line by default)
- application/platform request logs
- browser history and the `Referer` header
- any APM or error tracker capturing the connection URL

So a live credential is written to several persistent stores that are normally
considered safe to retain and share.

This is also inconsistent with every other authenticated endpoint in the app,
which uses `Depends(get_current_user)` and `HTTPBearer`.

### Reproduction

```bash
# The token is part of the URL; check the server access log afterwards.
websocat "ws://localhost:8000/ws/notifications?token=$TOKEN"
```

```
pytest tests/api/test_notifications_ws.py::TestKnownBugs::test_the_auth_token_travels_in_the_query_string
```

**Expected:** the token arrives in a header or a `Sec-WebSocket-Protocol` subprotocol.
**Actual:** a working connection whose URL embeds the bearer token.

### Suggested fix (not applied)

Read the token from the `Sec-WebSocket-Protocol` header (the standard workaround
for the browser WebSocket API's lack of custom headers), or issue a short-lived
single-use ticket from a REST endpoint and accept that in the query string
instead of the long-lived access token.

---

## NOTIF-04

**One failing row silently drops every later notification** · **Medium**

`backend/app/modules/notifications/route.py:87-98`

### Description

On connect, the endpoint flushes all unread notifications:

```python
for n in unread:
    try:
        await websocket.send_text(json.dumps({...}))
    except Exception:
        break
```

The handler is `break`, not `continue`. Any single row that fails to serialise or
send abandons **every remaining notification** — with no log line, no error
frame, and no signal to the client that the list was truncated. The client
believes it has received the complete unread set.

The same `try/except` also swallows genuine transport errors, so a mid-flush
network fault is indistinguishable from "you have no more notifications".

### Reproduction

Real serialisation failures are rare, so the reproduction injects one on the
middle of three unread rows and asserts the third never arrives:

```
pytest tests/api/test_notifications_ws.py::TestKnownBugs::test_one_failing_row_silently_drops_every_later_notification
```

**Expected:** skip the bad row and continue, or fail loudly.
**Actual:** only the first notification is delivered; the third is silently lost.

### Suggested fix (not applied)

Change `break` to `continue`, and log the skipped row. Reserve `break` for a
genuine `WebSocketDisconnect`.

---

## NOTIF-05

**A single NULL `created_at` makes the entire inbox return 500** · **Medium**

`backend/app/modules/notifications/models.py:22`, `backend/app/modules/notifications/schemas.py:15`

### Description

The model declares:

```python
created_at = Column(DateTime, default=datetime.utcnow)      # no nullable=False
```

`default=` is a **Python-side** default — it only applies when the ORM builds the
INSERT. The column itself is nullable, so any write that bypasses the ORM (a
migration, a bulk load, a manual `UPDATE`, a future raw-SQL insert) can leave it
NULL.

The response schema requires it:

```python
created_at: datetime      # required
```

One NULL row therefore fails response validation and **`GET /api/notifications`
returns 500 for that user permanently** — not just for the bad row, but for the
entire inbox. Every other notification becomes unreachable, and the user cannot
delete the offending row because the only delete endpoint needs an id they can no
longer retrieve.

The WebSocket path fails on the same row via `n.created_at.isoformat()` →
`AttributeError`, which then triggers [NOTIF-04](#notif-04).

### Reproduction

```sql
UPDATE notifications SET created_at = NULL WHERE id = '<some id>';
```
```bash
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/api/notifications" -H "$AUTH"   # 500
```

```
pytest tests/api/test_notifications_ws.py::TestKnownBugs::test_a_null_created_at_makes_the_whole_inbox_500
```

**Expected:** the column rejects NULL at the database level.
**Actual:** NULL is accepted on write and 500s on every subsequent read.

### Suggested fix (not applied)

`nullable=False, server_default=func.now()` on the column. The same pattern
appears on `goals.created_at` and `roadmaps.created_at`, which are worth checking
together.

---

## Investigated and dismissed

Recording these so they are not re-reported.

### Fire-and-forget `asyncio.create_task(notify(...))` · **Not reproduced**

`backend/app/modules/roadmap/route.py:39,64` dispatch their notification with:

```python
asyncio.create_task(notify(...))
```

No reference to the task is retained. The asyncio docs warn that the event loop
keeps only a weak reference, so a task can be garbage-collected mid-execution —
which would mean a silently lost notification. The goals router uses
`background_tasks.add_task` for the same job, so the two modules disagree.

I could not make it fail. Across repeated runs the notification is persisted
every time, because the coroutine reaches its first `await` and completes before
the loop has any reason to collect it. Since the standard here is that a bug must
have a reproduction, it is not being reported as one.

It remains a latent risk worth changing on principle — `background_tasks.add_task`
is already the house pattern and has none of this ambiguity — but no defect is
demonstrable today.

### `BackgroundTasks` mutable default argument · **Not a bug**

`backend/app/modules/goals/route.py:41,109` declare:

```python
background_tasks: BackgroundTasks = BackgroundTasks()
```

A mutable default evaluated once at import time normally means every request
shares one instance, which here would mean tasks accumulating across requests
and firing repeatedly.

That does not happen. FastAPI resolves `BackgroundTasks` by type annotation and
injects a fresh instance per request, ignoring the default entirely. Verified by
`test_recompleting_a_goal_fires_a_duplicate_notification`: three PATCH requests
produce exactly 3 notifications. A shared, accumulating instance would produce 6
(1 + 2 + 3).

Still worth deleting as a misleading pattern, but it has no runtime effect.
