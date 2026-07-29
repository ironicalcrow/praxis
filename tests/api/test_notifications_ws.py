"""
Tests for the `/ws/notifications` WebSocket endpoint
(`app/modules/notifications/route.py:63`, mounted in `main.py:45`).

Unlike the REST routes this one does NOT use `Depends(get_current_user)` — it
authenticates by calling `supabase.auth.get_user(token)` directly, with the token
arriving as a **query parameter**. So these tests patch the Supabase stub rather
than overriding a dependency.

Note the endpoint is mounted at the app root, not under `/api`.
"""

import json
import threading
import types
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from starlette.websockets import WebSocketDisconnect

from helpers import make_notification

pytestmark = pytest.mark.ws

WS_URL = "/ws/notifications"


def receive_or_none(ws, timeout: float = 1.0):
    """
    `WebSocketTestSession.receive_text()` blocks forever when nothing is queued,
    and exposes no non-blocking variant — so asserting that *no* frame arrives
    needs a bounded read. Returns the decoded frame, or None on timeout.
    """
    box = []

    def _read():
        try:
            box.append(ws.receive_text())
        except Exception:
            # The socket closes out from under this thread when the enclosing
            # `with` block exits — that is the "nothing arrived" case, not a fault.
            pass

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    return json.loads(box[0]) if box else None


@pytest.fixture
def ws_auth(monkeypatch, user):
    """
    Point `supabase.auth.get_user` at a fake.

    `token` values map to outcomes:
      "valid-token" -> the seeded `user`
      "no-user"     -> a response whose `.user` is None
      anything else -> raises, as the real client does for a bad JWT
    """
    import app.core.supabase as supa

    def _get_user(tok):
        if tok == "valid-token":
            return types.SimpleNamespace(user=types.SimpleNamespace(id=user.id))
        if tok == "no-user":
            return types.SimpleNamespace(user=None)
        raise ValueError("invalid JWT")

    monkeypatch.setattr(supa.supabase.auth, "get_user", _get_user)
    return user


# ── Authentication ─────────────────────────────────────────────────────────────

class TestWebSocketAuth:
    def test_a_missing_token_is_refused(self, client, ws_auth):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(WS_URL):
                pass

        assert exc.value.code == 4001

    def test_an_empty_token_is_refused(self, client, ws_auth):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"{WS_URL}?token="):
                pass

        assert exc.value.code == 4001

    def test_a_token_that_resolves_to_no_user_is_refused(self, client, ws_auth):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"{WS_URL}?token=no-user"):
                pass

        assert exc.value.code == 4001

    def test_a_token_that_raises_is_refused(self, client, ws_auth):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"{WS_URL}?token=garbage"):
                pass

        assert exc.value.code == 4001

    def test_a_valid_token_is_accepted(self, client, ws_auth):
        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            assert ws is not None


# ── Unread flush on connect ────────────────────────────────────────────────────

class TestUnreadFlushOnConnect:
    def test_nothing_is_sent_when_there_is_no_unread(self, client, db, ws_auth):
        make_notification(db, ws_auth.id, is_read=True)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            assert receive_or_none(ws) is None

    def test_every_unread_notification_is_pushed(self, client, db, ws_auth):
        make_notification(db, ws_auth.id, title="A", is_read=False)
        make_notification(db, ws_auth.id, title="B", is_read=False)
        make_notification(db, ws_auth.id, title="C", is_read=False)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            received = [json.loads(ws.receive_text()) for _ in range(3)]

        assert {n["title"] for n in received} == {"A", "B", "C"}

    def test_read_notifications_are_not_pushed(self, client, db, ws_auth):
        make_notification(db, ws_auth.id, title="Unread", is_read=False)
        make_notification(db, ws_auth.id, title="Read", is_read=True)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            first = json.loads(ws.receive_text())

        assert first["title"] == "Unread"

    def test_another_users_notifications_are_not_pushed(self, client, db, ws_auth, other_user):
        make_notification(db, ws_auth.id, title="Mine", is_read=False)
        make_notification(db, other_user.id, title="Theirs", is_read=False)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            first = json.loads(ws.receive_text())

        assert first["title"] == "Mine"

    def test_the_frame_shape(self, client, db, ws_auth):
        make_notification(db, ws_auth.id, type="goal_completed", data={"goal_id": "g1"})

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            frame = json.loads(ws.receive_text())

        assert set(frame) == {
            "id", "type", "title", "message", "data", "is_read", "created_at",
        }
        assert frame["type"] == "goal_completed"
        assert frame["data"] == {"goal_id": "g1"}
        assert frame["is_read"] is False

    def test_the_frame_omits_user_id(self, client, db, ws_auth):
        """The REST shape includes user_id; the WS frame does not. Documenting the drift."""
        make_notification(db, ws_auth.id)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            frame = json.loads(ws.receive_text())

        assert "user_id" not in frame


# ── Connection lifecycle ───────────────────────────────────────────────────────

class TestConnectionLifecycle:
    def test_the_user_is_registered_while_connected(self, client, ws_auth):
        from app.modules.notifications.ws_manager import manager

        with client.websocket_connect(f"{WS_URL}?token=valid-token"):
            assert ws_auth.id in manager._connections

    def test_disconnecting_deregisters_the_user(self, client, ws_auth):
        from app.modules.notifications.ws_manager import manager

        with client.websocket_connect(f"{WS_URL}?token=valid-token"):
            pass

        assert ws_auth.id not in manager._connections

    def test_a_refused_connection_is_never_registered(self, client, ws_auth):
        from app.modules.notifications.ws_manager import manager

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"{WS_URL}?token=garbage"):
                pass

        assert ws_auth.id not in manager._connections


# ── Bug reproductions ──────────────────────────────────────────────────────────

class TestKnownBugs:
    """
    Each test asserts the behaviour the endpoint SHOULD have, and is marked
    `xfail(strict=True)` because it does not have it yet. See `tests/README.md`.
    """

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-03: token accepted as a query parameter")
    def test_a_query_string_token_is_refused(self, client, ws_auth):
        """
        NOTIF-03 — the Supabase access token is accepted as a URL query
        parameter, so a live credential is written to reverse-proxy access logs,
        browser history, and the `Referer` header. Every other authenticated
        endpoint takes it in a header via `HTTPBearer`.

        The fix is to read it from `Sec-WebSocket-Protocol`, or to issue a
        short-lived single-use ticket — after which a query-string access token
        should be rejected.
        """
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"{WS_URL}?token=valid-token"):
                pass

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-04: flush loop uses `break`, not `continue`")
    def test_one_failing_row_does_not_drop_the_rest(
        self, client, db, ws_auth, monkeypatch
    ):
        """
        NOTIF-04 — the flush loop at `route.py:87-98` wraps each send in
        `try/except Exception: break`. `break`, not `continue` — so a single row
        that fails to serialise abandons every remaining notification, with no
        log, no error frame, and no indication to the client that the list was
        truncated.

        The failure is injected here (real triggers are rare), but the control
        flow it exercises is the product's.
        """
        import app.modules.notifications.route as route_mod

        now = datetime.utcnow()
        make_notification(db, ws_auth.id, title="Newest", is_read=False, created_at=now)
        make_notification(
            db, ws_auth.id, title="Broken", is_read=False,
            created_at=now - timedelta(hours=1),
        )
        make_notification(
            db, ws_auth.id, title="Oldest", is_read=False,
            created_at=now - timedelta(hours=2),
        )

        real_dumps = json.dumps

        def failing_dumps(obj, *a, **kw):
            if isinstance(obj, dict) and obj.get("title") == "Broken":
                raise TypeError("Object of type X is not JSON serializable")
            return real_dumps(obj, *a, **kw)

        monkeypatch.setattr(route_mod.json, "dumps", failing_dumps)

        with client.websocket_connect(f"{WS_URL}?token=valid-token") as ws:
            first = receive_or_none(ws)
            second = receive_or_none(ws)

        assert first["title"] == "Newest"
        assert second is not None and second["title"] == "Oldest"

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-05: created_at column is nullable")
    def test_a_null_created_at_cannot_break_the_inbox(self, client, db, ws_auth):
        """
        NOTIF-05 — `notifications/models.py:22` declares `created_at` with only a
        Python-side default and no `nullable=False`, so the column accepts NULL.
        `NotificationOut.created_at` is a required `datetime`, so one NULL row
        fails response validation and takes down `GET /api/notifications`
        entirely — every other notification becomes unreachable, and the user
        cannot delete the offending row without knowing its id.

        The fix is `nullable=False` on the column, after which this write fails
        instead of the read.
        """
        good = make_notification(db, ws_auth.id, title="Fine")
        db.execute(
            text("UPDATE notifications SET created_at = NULL WHERE id = :i"),
            {"i": good.id},
        )
        db.commit()

        assert client.get("/api/notifications").status_code == 200
