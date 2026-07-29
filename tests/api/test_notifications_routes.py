"""
HTTP-layer tests for the REST half of `app/modules/notifications/route.py`
(4 endpoints). The WebSocket half is covered in `test_notifications_ws.py`.

Tests marked `@pytest.mark.bug` assert the behaviour the code SHOULD have and
carry `xfail(strict=True)`, so they report as `xfailed` rather than passing. Each
names its BUG_REPORT.md id. Fixing the bug turns one into an XPASS, which
`strict` escalates to a hard failure — the prompt to drop the marker.
"""

from datetime import datetime, timedelta

import pytest

from helpers import MISSING_UUID, make_notification, notifications_for

pytestmark = pytest.mark.api


# ── GET /api/notifications ─────────────────────────────────────────────────────

class TestListNotifications:
    def test_no_notifications_returns_an_empty_list(self, client):
        r = client.get("/api/notifications")

        assert r.status_code == 200
        assert r.json() == []

    def test_notifications_are_returned_for_the_authenticated_user(self, client, db, user):
        make_notification(db, user.id, title="First")
        make_notification(db, user.id, title="Second")

        r = client.get("/api/notifications")

        assert r.status_code == 200
        assert {n["title"] for n in r.json()} == {"First", "Second"}

    def test_another_users_notifications_are_not_visible(self, client, db, user, other_user):
        make_notification(db, user.id, title="Mine")
        make_notification(db, other_user.id, title="Theirs")

        r = client.get("/api/notifications")

        assert [n["title"] for n in r.json()] == ["Mine"]

    def test_newest_first(self, client, db, user):
        now = datetime.utcnow()
        make_notification(db, user.id, title="Oldest", created_at=now - timedelta(hours=2))
        make_notification(db, user.id, title="Newest", created_at=now)
        make_notification(db, user.id, title="Middle", created_at=now - timedelta(hours=1))

        body = client.get("/api/notifications").json()

        assert [n["title"] for n in body] == ["Newest", "Middle", "Oldest"]

    def test_unread_only_filters_out_read_notifications(self, client, db, user):
        make_notification(db, user.id, title="Unread", is_read=False)
        make_notification(db, user.id, title="Read", is_read=True)

        body = client.get("/api/notifications", params={"unread_only": True}).json()

        assert [n["title"] for n in body] == ["Unread"]

    def test_unread_only_defaults_to_false(self, client, db, user):
        make_notification(db, user.id, title="Unread", is_read=False)
        make_notification(db, user.id, title="Read", is_read=True)

        assert len(client.get("/api/notifications").json()) == 2

    def test_the_response_shape(self, client, db, user):
        make_notification(db, user.id, data={"goal_id": "abc"})

        body = client.get("/api/notifications").json()[0]

        assert set(body) == {
            "id", "user_id", "type", "title", "message", "data", "is_read", "created_at",
        }
        assert body["data"] == {"goal_id": "abc"}
        assert body["is_read"] is False

    def test_a_null_data_payload_is_returned_as_none(self, client, db, user):
        make_notification(db, user.id, data=None)

        assert client.get("/api/notifications").json()[0]["data"] is None

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.get("/api/notifications")

        assert r.status_code in (401, 403)


# ── PATCH /api/notifications/{id}/read ─────────────────────────────────────────

class TestMarkNotificationRead:
    def test_a_notification_is_marked_read(self, client, db, user):
        n = make_notification(db, user.id, is_read=False)

        r = client.patch(f"/api/notifications/{n.id}/read")

        assert r.status_code == 200
        assert r.json()["is_read"] is True

    def test_the_change_is_persisted(self, client, db, user):
        n = make_notification(db, user.id, is_read=False)

        client.patch(f"/api/notifications/{n.id}/read")

        db.expire_all()
        assert notifications_for(db, user.id)[0].is_read is True

    def test_marking_an_already_read_notification_is_idempotent(self, client, db, user):
        n = make_notification(db, user.id, is_read=True)

        r = client.patch(f"/api/notifications/{n.id}/read")

        assert r.status_code == 200
        assert r.json()["is_read"] is True

    def test_only_the_target_notification_changes(self, client, db, user):
        target = make_notification(db, user.id, title="Target", is_read=False)
        make_notification(db, user.id, title="Untouched", is_read=False)

        client.patch(f"/api/notifications/{target.id}/read")

        db.expire_all()
        untouched = [n for n in notifications_for(db, user.id) if n.title == "Untouched"][0]
        assert untouched.is_read is False

    def test_an_unknown_notification_is_404(self, client):
        r = client.patch(f"/api/notifications/{MISSING_UUID}/read")

        assert r.status_code == 404
        assert r.json()["detail"] == "Notification not found"

    def test_another_users_notification_is_404(self, client, db, other_user):
        n = make_notification(db, other_user.id)

        r = client.patch(f"/api/notifications/{n.id}/read")

        assert r.status_code == 404

    def test_another_users_notification_is_not_modified(self, client, db, other_user):
        n = make_notification(db, other_user.id, is_read=False)

        client.patch(f"/api/notifications/{n.id}/read")

        db.expire_all()
        assert notifications_for(db, other_user.id)[0].is_read is False

    def test_a_non_uuid_id_is_422(self, client):
        r = client.patch("/api/notifications/not-a-uuid/read")

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client, db, user):
        n = make_notification(db, user.id)

        r = anon_client.patch(f"/api/notifications/{n.id}/read")

        assert r.status_code in (401, 403)


# ── POST /api/notifications/mark-all-read ──────────────────────────────────────

class TestMarkAllRead:
    def test_all_unread_are_marked_and_counted(self, client, db, user):
        make_notification(db, user.id, is_read=False)
        make_notification(db, user.id, is_read=False)
        make_notification(db, user.id, is_read=False)

        r = client.post("/api/notifications/mark-all-read")

        assert r.status_code == 200
        assert r.json() == {"marked_read": 3}

    def test_already_read_notifications_are_not_counted(self, client, db, user):
        make_notification(db, user.id, is_read=False)
        make_notification(db, user.id, is_read=True)

        assert client.post("/api/notifications/mark-all-read").json() == {"marked_read": 1}

    def test_nothing_unread_reports_zero(self, client, db, user):
        make_notification(db, user.id, is_read=True)

        assert client.post("/api/notifications/mark-all-read").json() == {"marked_read": 0}

    def test_an_empty_inbox_reports_zero(self, client):
        assert client.post("/api/notifications/mark-all-read").json() == {"marked_read": 0}

    def test_another_users_notifications_are_untouched(self, client, db, user, other_user):
        make_notification(db, user.id, is_read=False)
        make_notification(db, other_user.id, is_read=False)

        r = client.post("/api/notifications/mark-all-read")

        assert r.json() == {"marked_read": 1}
        db.expire_all()
        assert notifications_for(db, other_user.id)[0].is_read is False

    def test_the_inbox_is_empty_afterwards_when_filtering_unread(self, client, db, user):
        make_notification(db, user.id, is_read=False)
        make_notification(db, user.id, is_read=False)

        client.post("/api/notifications/mark-all-read")

        assert client.get("/api/notifications", params={"unread_only": True}).json() == []

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.post("/api/notifications/mark-all-read")

        assert r.status_code in (401, 403)


# ── DELETE /api/notifications/{id} ─────────────────────────────────────────────

class TestDeleteNotification:
    def test_a_notification_is_deleted_with_204_and_no_body(self, client, db, user):
        n = make_notification(db, user.id)

        r = client.delete(f"/api/notifications/{n.id}")

        assert r.status_code == 204
        assert r.content == b""
        assert notifications_for(db, user.id) == []

    def test_only_the_target_is_deleted(self, client, db, user):
        target = make_notification(db, user.id, title="Target")
        make_notification(db, user.id, title="Survivor")

        client.delete(f"/api/notifications/{target.id}")

        assert [n.title for n in notifications_for(db, user.id)] == ["Survivor"]

    def test_an_unknown_notification_is_404(self, client):
        r = client.delete(f"/api/notifications/{MISSING_UUID}")

        assert r.status_code == 404

    def test_another_users_notification_cannot_be_deleted(self, client, db, other_user):
        n = make_notification(db, other_user.id)

        r = client.delete(f"/api/notifications/{n.id}")

        assert r.status_code == 404
        assert len(notifications_for(db, other_user.id)) == 1

    def test_a_second_delete_is_404(self, client, db, user):
        n = make_notification(db, user.id)

        client.delete(f"/api/notifications/{n.id}")
        r = client.delete(f"/api/notifications/{n.id}")

        assert r.status_code == 404

    def test_a_non_uuid_id_is_422(self, client):
        r = client.delete("/api/notifications/not-a-uuid")

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client, db, user):
        n = make_notification(db, user.id)

        r = anon_client.delete(f"/api/notifications/{n.id}")

        assert r.status_code in (401, 403)


# ── Bug reproductions ──────────────────────────────────────────────────────────

class TestKnownBugs:
    """
    Each test asserts the behaviour the endpoint SHOULD have, and is marked
    `xfail(strict=True)` because it does not have it yet. See `tests/README.md`.
    """

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-01: the inbox has no pagination")
    def test_the_inbox_is_bounded(self, client, db, user):
        """
        NOTIF-01 — `GET /api/notifications` takes no limit, offset, or cursor and
        applies no `.limit()`, so it returns every notification the user has ever
        accumulated. Notifications are produced by ordinary activity and never
        expire, so this grows without bound.
        """
        from app.modules.notifications.models import Notification

        db.bulk_save_objects([
            Notification(
                user_id=user.id, type="goal_completed",
                title=f"n{i}", message="m", is_read=False,
            )
            for i in range(250)
        ])
        db.commit()

        body = client.get("/api/notifications").json()

        assert len(body) < 250

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-01: unread_only is the only parameter")
    def test_pagination_parameters_are_offered(self, client):
        """
        NOTIF-01 — the OpenAPI schema confirms `unread_only` is the only knob.
        `chat/route.py:70` already implements the `limit` + `before` pattern this
        endpoint should follow.
        """
        schema = client.get("/openapi.json").json()

        params = schema["paths"]["/api/notifications"]["get"].get("parameters", [])
        names = {p["name"] for p in params}

        assert names & {"limit", "offset", "before", "page"}

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="NOTIF-02: mark-all-read has no response_model")
    def test_mark_all_read_declares_a_response_model(self, client):
        """
        NOTIF-02 — `route.py:41` declares no `response_model`, so the
        `{"marked_read": int}` contract is neither validated nor documented.
        Every other notifications endpoint declares one.
        """
        schema = client.get("/openapi.json").json()

        content = (
            schema["paths"]["/api/notifications/mark-all-read"]["post"]
            ["responses"]["200"]["content"]["application/json"]
        )

        assert content.get("schema")

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-07: collection route registered as ''")
    def test_trailing_slash_serves_the_collection(self, client):
        """GOALS-07 — third module with the same defect: `/api/notifications/` 307s."""
        r = client.get("/api/notifications/", follow_redirects=False)

        assert r.status_code == 200
