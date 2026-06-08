# Notification System

## Overview

The notification system delivers real-time alerts to connected users via WebSocket and persists every notification in PostgreSQL so offline users never miss anything. Redis Pub/Sub is the real-time transport layer; the database is the source of truth.

---

## Architecture

```
Event triggers in any module
          │
          ▼
create_and_publish(user_id, type, title, message, data)
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
INSERT into    PUBLISH to Redis
notifications  user:{user_id}:notifications
table (DB)     channel
                    │
                    ▼ (only if user has active WebSocket)
             WebSocket listener receives
             and pushes JSON to client
```

**Two independent paths run on every notification:**
1. **DB write** — always happens, regardless of whether the user is online
2. **Redis publish** — fires immediately; if nobody is subscribed, the message is simply dropped (not an error)

---

## WebSocket — Real-Time Delivery

### Endpoint
```
WS /ws/notifications?token=<bearer_token>
```

**Auth:** Token is passed as a query parameter because browsers cannot set custom headers on WebSocket connections. The token is validated against Supabase (`supabase.auth.get_user(token)`) before the connection is accepted.

### On Connect
1. Token validated — connection rejected with code `4001` if invalid
2. All **unread** notifications are fetched from DB and pushed to the client immediately (catch-up for missed notifications)
3. A Redis subscriber is started for the channel `user:{user_id}:notifications`
4. Any new notification published to that channel is forwarded to the WebSocket client in real time

### On Disconnect
- Redis subscriber is cancelled and cleaned up
- Connection is removed from the manager
- No data is lost — notifications remain in DB

### Multiple Tabs
The connection manager supports multiple simultaneous WebSocket connections per user (e.g. two browser tabs). Each connection gets its own Redis subscriber and receives all notifications independently.

---

## Offline User Handling

When a user has no active WebSocket connection:

1. `create_and_publish()` still writes the notification to the `notifications` table with `is_read = False`
2. The Redis publish fires but is silently dropped (no subscriber)
3. When the user reconnects via WebSocket, the on-connect handler fetches all unread notifications from DB and pushes them before subscribing to Redis
4. The user sees every notification they missed — in order, oldest first

There is no message loss. Redis is used only for real-time delivery; the DB is authoritative.

---

## Notification Triggers

Notifications fire automatically from the following events:

| Event | Type | Module |
|-------|------|--------|
| CV uploaded and parsed | `cv_parsed` | `CV/route.py` |
| Past CV version activated | `cv_activated` | `CV/route.py` |
| Job suggestion pool built | `job_suggestions_ready` | `jobs/services/job_suggestion.py` |
| Job saved to application tracker | `application_saved` | `application/route.py` |
| Application status → applied / interviewing / offer / rejected | `application_status_changed` | `application/route.py` |
| Goal marked as completed | `goal_completed` | `goals/route.py` |
| Roadmap milestones converted to goals | `goals_created_from_roadmap` | `goals/route.py` |
| Roadmap generated from conversation | `roadmap_generated` | `roadmap/route.py` |
| Roadmap generated from job gap analysis | `roadmap_generated` | `roadmap/route.py` |
| Coaching conversation auto-summarized (session rotation) | `conversation_summarized` | `chat/service.py` |
| Coaching session detects skill gap → nudge user to build roadmap | `coach_roadmap_nudge` | `chat/service.py` |
| Cover letter draft generated | `cover_letter_ready` | `cover_letter/route.py` |

---

## REST Endpoints

All REST endpoints require `Authorization: Bearer <token>`.

### List notifications
```
GET /api/notifications
GET /api/notifications?unread_only=true
```
Returns all notifications for the authenticated user, newest first. Use `unread_only=true` to filter to unread only.

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "type": "cv_parsed",
    "title": "CV uploaded and parsed",
    "message": "Your CV has been processed. Job suggestions will refresh shortly.",
    "data": { "resume_id": "uuid" },
    "is_read": false,
    "created_at": "2026-06-07T12:00:00"
  }
]
```

### Mark one notification as read
```
PATCH /api/notifications/{id}/read
```
Sets `is_read = true` for the given notification. Returns the updated notification object.

### Mark all notifications as read
```
POST /api/notifications/mark-all-read
```
Marks every unread notification for the user as read.

**Response:**
```json
{ "marked_read": 5 }
```

### Delete a notification
```
DELETE /api/notifications/{id}
```
Permanently removes the notification. Returns `204 No Content`.

---

## Notification Payload (WebSocket)

Every message pushed over WebSocket (both on-connect catch-up and real-time) is a JSON string:

```json
{
  "id": "uuid",
  "type": "goal_completed",
  "title": "Goal completed!",
  "message": "You completed \"Learn React Hooks\". Keep up the momentum!",
  "data": { "goal_id": "uuid" },
  "is_read": false,
  "created_at": "2026-06-07T12:34:56"
}
```

---

## Database Schema

```sql
CREATE TABLE notifications (
    id          VARCHAR PRIMARY KEY,
    user_id     VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50) NOT NULL,
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    data        JSON,
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## File Structure

```
backend/app/modules/notifications/
├── __init__.py
├── models.py       — SQLAlchemy Notification model
├── schemas.py      — Pydantic NotificationOut schema
├── db_service.py   — create, list, mark_read, mark_all_read, delete
├── service.py      — create_and_publish() (DB write + Redis publish)
├── ws_manager.py   — WebSocket connection manager + Redis subscriber
└── route.py        — REST endpoints + ws_notifications WebSocket handler
```

---

## Testing

### Connect via browser console (from `http://localhost:8000/api/docs`)
```javascript
const token = "YOUR_BEARER_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);

ws.onopen    = () => console.log("✅ Connected");
ws.onmessage = (e) => console.log("🔔 Notification:", JSON.parse(e.data));
ws.onclose   = (e) => console.log("🔌 Closed:", e.code, e.reason);
```

### Trigger a notification
- Upload a CV via `POST /api/cv/upload-cv` → fires `cv_parsed`
- Mark a goal completed via `PATCH /api/goals/{id}` with `{"status": "completed"}` → fires `goal_completed`
- Change an application status via `PATCH /api/application/applications/{id}/status` → fires `application_status_changed`

### Verify offline queuing
1. Close the WebSocket connection
2. Trigger any event above
3. Reconnect — the missed notification arrives immediately on connect
4. Or call `GET /api/notifications?unread_only=true` to see it in DB
