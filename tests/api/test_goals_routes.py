"""
HTTP-layer tests for `app/modules/goals/route.py` (6 endpoints).

Scope note: the goals *db_service* is already covered elsewhere. Everything here
drives the router through TestClient — status codes, auth, validation, ownership
scoping, and the request/response contract.

Tests marked `@pytest.mark.bug` assert the behaviour the code SHOULD have and
carry `xfail(strict=True)`, so they report as `xfailed` rather than passing. Each
names its BUG_REPORT.md id. Fixing the bug turns one into an XPASS, which
`strict` escalates to a hard failure — the prompt to drop the marker.
"""

from datetime import date, timedelta

import pytest

from helpers import (
    MISSING_UUID,
    goals_for,
    make_goal,
    make_roadmap,
    make_roadmap_with_milestones,
    notifications_for,
)

pytestmark = pytest.mark.api


# ── POST /api/goals ────────────────────────────────────────────────────────────

class TestCreateGoal:
    def test_a_minimal_goal_is_created_with_201(self, client):
        r = client.post("/api/goals", json={"title": "Learn Rust"})

        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Learn Rust"
        assert body["status"] == "not_started"
        assert body["source_type"] == "manual"
        assert body["roadmap_id"] is None
        assert body["milestone_id"] is None

    def test_description_and_target_date_are_persisted(self, client):
        target = (date.today() + timedelta(days=30)).isoformat()

        r = client.post(
            "/api/goals",
            json={"title": "Ship v1", "description": "Cut the release", "target_date": target},
        )

        assert r.status_code == 201
        assert r.json()["description"] == "Cut the release"
        assert r.json()["target_date"] == target

    def test_the_goal_is_owned_by_the_authenticated_user(self, client, user):
        r = client.post("/api/goals", json={"title": "Mine"})

        assert r.json()["user_id"] == user.id

    def test_a_missing_title_is_rejected(self, client):
        r = client.post("/api/goals", json={"description": "no title"})

        assert r.status_code == 422

    def test_a_malformed_target_date_is_rejected(self, client):
        r = client.post("/api/goals", json={"title": "Bad date", "target_date": "31-12-2026"})

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.post("/api/goals", json={"title": "Sneaky"})

        assert r.status_code in (401, 403)


# ── POST /api/goals/from-roadmap/{roadmap_id} ──────────────────────────────────

class TestCreateGoalsFromRoadmap:
    def test_every_milestone_is_promoted_when_no_body_is_sent(self, client, db, user):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)

        r = client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert r.status_code == 201
        body = r.json()
        assert len(body) == len(milestones)
        assert {g["title"] for g in body} == {m.title for m in milestones}
        assert all(g["source_type"] == "roadmap" for g in body)
        assert all(g["roadmap_id"] == roadmap.id for g in body)

    def test_only_the_requested_milestones_are_promoted(self, client, db, user):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)

        r = client.post(
            f"/api/goals/from-roadmap/{roadmap.id}",
            json={"milestone_ids": [milestones[0].id]},
        )

        assert r.status_code == 201
        assert [g["title"] for g in r.json()] == [milestones[0].title]

    def test_an_empty_milestone_id_list_promotes_everything(self, client, db, user):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)

        r = client.post(f"/api/goals/from-roadmap/{roadmap.id}", json={"milestone_ids": []})

        assert r.status_code == 201
        assert len(r.json()) == len(milestones)

    def test_promotion_emits_a_notification(self, client, db, user):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)

        client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        notifications = notifications_for(db, user.id)
        assert len(notifications) == 1
        assert notifications[0].type == "goals_created_from_roadmap"
        assert notifications[0].data["goal_count"] == len(milestones)

    def test_a_roadmap_with_no_milestones_yields_no_goals(self, client, db, user):
        roadmap = make_roadmap(db, user.id)

        r = client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert r.status_code == 201
        assert r.json() == []

    def test_an_unknown_roadmap_is_404(self, client):
        r = client.post(f"/api/goals/from-roadmap/{MISSING_UUID}")

        assert r.status_code == 404
        assert r.json()["detail"] == "Roadmap not found"

    def test_another_users_roadmap_is_404(self, client, db, other_user):
        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, other_user.id)

        r = client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert r.status_code == 404

    def test_the_owner_can_still_promote_their_own_roadmap(self, as_user, db, other_user):
        """Counterpart to the 404 above — proves that test asserts scoping, not breakage."""
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, other_user.id)

        r = as_user(other_user).post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert r.status_code == 201
        assert len(r.json()) == len(milestones)

    def test_a_non_uuid_roadmap_id_is_422(self, client):
        r = client.post("/api/goals/from-roadmap/not-a-uuid")

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client, db, user):
        roadmap, _phase, _m = make_roadmap_with_milestones(db, user.id)

        r = anon_client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert r.status_code in (401, 403)


# ── GET /api/goals ─────────────────────────────────────────────────────────────

class TestListGoals:
    def test_an_empty_tracker_returns_an_empty_list(self, client):
        r = client.get("/api/goals")

        assert r.status_code == 200
        assert r.json() == []

    def test_goals_are_returned_for_the_authenticated_user(self, client, db, user):
        make_goal(db, user.id, title="First")
        make_goal(db, user.id, title="Second")

        r = client.get("/api/goals")

        assert r.status_code == 200
        assert {g["title"] for g in r.json()} == {"First", "Second"}

    def test_another_users_goals_are_not_visible(self, client, db, user, other_user):
        make_goal(db, user.id, title="Mine")
        make_goal(db, other_user.id, title="Theirs")

        r = client.get("/api/goals")

        assert [g["title"] for g in r.json()] == ["Mine"]

    @pytest.mark.parametrize("status", ["not_started", "in_progress", "completed", "paused"])
    def test_each_valid_status_filters(self, client, db, user, status):
        make_goal(db, user.id, title="Match", status=status)
        make_goal(db, user.id, title="NoMatch", status="in_progress" if status != "in_progress" else "paused")

        r = client.get("/api/goals", params={"status": status})

        assert r.status_code == 200
        assert [g["title"] for g in r.json()] == ["Match"]

    def test_an_invalid_status_is_400_not_422(self, client):
        r = client.get("/api/goals", params={"status": "done"})

        assert r.status_code == 400
        assert "Invalid status" in r.json()["detail"]

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.get("/api/goals")

        assert r.status_code in (401, 403)


# ── GET /api/goals/{goal_id} ───────────────────────────────────────────────────

class TestGetGoal:
    def test_a_goal_is_returned_with_its_full_shape(self, client, db, user):
        goal = make_goal(db, user.id, title="Read the docs")

        r = client.get(f"/api/goals/{goal.id}")

        assert r.status_code == 200
        body = r.json()
        assert set(body) == {
            "id", "user_id", "title", "description", "status", "source_type",
            "roadmap_id", "milestone_id", "target_date", "created_at", "updated_at",
        }
        assert body["title"] == "Read the docs"

    def test_an_unknown_goal_is_404(self, client):
        r = client.get(f"/api/goals/{MISSING_UUID}")

        assert r.status_code == 404
        assert r.json()["detail"] == "Goal not found"

    def test_another_users_goal_is_404(self, client, db, other_user):
        goal = make_goal(db, other_user.id, title="Theirs")

        r = client.get(f"/api/goals/{goal.id}")

        assert r.status_code == 404

    def test_a_non_uuid_goal_id_is_422(self, client):
        r = client.get("/api/goals/not-a-uuid")

        assert r.status_code == 422


# ── PATCH /api/goals/{goal_id} ─────────────────────────────────────────────────

class TestUpdateGoal:
    def test_the_title_is_updated(self, client, db, user):
        goal = make_goal(db, user.id, title="Old")

        r = client.patch(f"/api/goals/{goal.id}", json={"title": "New"})

        assert r.status_code == 200
        assert r.json()["title"] == "New"

    def test_the_status_is_updated(self, client, db, user):
        goal = make_goal(db, user.id, status="not_started")

        r = client.patch(f"/api/goals/{goal.id}", json={"status": "in_progress"})

        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_an_empty_body_is_a_no_op_that_still_returns_the_goal(self, client, db, user):
        goal = make_goal(db, user.id, title="Unchanged")

        r = client.patch(f"/api/goals/{goal.id}", json={})

        assert r.status_code == 200
        assert r.json()["title"] == "Unchanged"

    def test_an_invalid_status_is_400(self, client, db, user):
        goal = make_goal(db, user.id)

        r = client.patch(f"/api/goals/{goal.id}", json={"status": "finished"})

        assert r.status_code == 400
        assert "Invalid status" in r.json()["detail"]

    def test_status_validation_runs_before_the_goal_is_looked_up(self, client):
        """An unknown goal AND an invalid status reports the status problem first."""
        r = client.patch(f"/api/goals/{MISSING_UUID}", json={"status": "finished"})

        assert r.status_code == 400

    def test_an_unknown_goal_is_404(self, client):
        r = client.patch(f"/api/goals/{MISSING_UUID}", json={"title": "New"})

        assert r.status_code == 404

    def test_another_users_goal_cannot_be_updated(self, client, db, other_user):
        goal = make_goal(db, other_user.id, title="Theirs")

        r = client.patch(f"/api/goals/{goal.id}", json={"title": "Hijacked"})

        assert r.status_code == 404

    def test_completing_a_goal_emits_a_notification(self, client, db, user):
        goal = make_goal(db, user.id, title="Finish course", status="in_progress")

        r = client.patch(f"/api/goals/{goal.id}", json={"status": "completed"})

        assert r.status_code == 200
        notifications = notifications_for(db, user.id)
        assert len(notifications) == 1
        assert notifications[0].type == "goal_completed"
        assert "Finish course" in notifications[0].message

    def test_a_non_completing_update_emits_no_notification(self, client, db, user):
        goal = make_goal(db, user.id, status="not_started")

        client.patch(f"/api/goals/{goal.id}", json={"status": "in_progress"})

        assert notifications_for(db, user.id) == []


# ── DELETE /api/goals/{goal_id} ────────────────────────────────────────────────

class TestDeleteGoal:
    def test_a_goal_is_deleted_with_204_and_no_body(self, client, db, user):
        goal = make_goal(db, user.id)

        r = client.delete(f"/api/goals/{goal.id}")

        assert r.status_code == 204
        assert r.content == b""
        assert goals_for(db, user.id) == []

    def test_an_unknown_goal_is_404(self, client):
        r = client.delete(f"/api/goals/{MISSING_UUID}")

        assert r.status_code == 404

    def test_another_users_goal_cannot_be_deleted(self, client, db, other_user):
        goal = make_goal(db, other_user.id)

        r = client.delete(f"/api/goals/{goal.id}")

        assert r.status_code == 404
        assert len(goals_for(db, other_user.id)) == 1

    def test_a_second_delete_is_404(self, client, db, user):
        goal = make_goal(db, user.id)

        client.delete(f"/api/goals/{goal.id}")
        r = client.delete(f"/api/goals/{goal.id}")

        assert r.status_code == 404


# ── Bug reproductions ──────────────────────────────────────────────────────────

class TestKnownBugs:
    """
    Each test asserts the behaviour the endpoint SHOULD have, and is marked
    `xfail(strict=True)` because it does not have it yet. They report as
    `xfailed`, so the bug count is visible in the run output. When a bug is
    fixed the test XPASSes, which `strict` turns into a hard failure — the
    signal to drop the marker and close the entry in BUG_REPORT.md.
    """

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-01: exclude_none strips explicit nulls")
    def test_target_date_can_be_cleared(self, client, db, user):
        """
        GOALS-01 — `route.py:114` uses `model_dump(exclude_none=True)`, so an
        explicit JSON null is stripped before it reaches the db layer and the
        old value survives. `exclude_unset=True` is the correct switch.
        """
        target = date.today() + timedelta(days=10)
        goal = make_goal(db, user.id, target_date=target)

        r = client.patch(f"/api/goals/{goal.id}", json={"target_date": None})

        assert r.status_code == 200
        assert r.json()["target_date"] is None

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-01: exclude_none strips explicit nulls")
    def test_description_can_be_cleared(self, client, db, user):
        """GOALS-01 — same root cause, second field."""
        goal = make_goal(db, user.id, description="Original text")

        r = client.patch(f"/api/goals/{goal.id}", json={"description": None})

        assert r.json()["description"] is None

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-02: promotion is not idempotent")
    def test_promoting_a_roadmap_twice_is_idempotent(self, client, db, user):
        """
        GOALS-02 — `create_goals_from_milestones` never checks whether a goal
        already exists for a milestone, and no unique constraint stops it, so a
        double-click doubles the user's tracker.
        """
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)

        client.post(f"/api/goals/from-roadmap/{roadmap.id}")
        client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        assert len(goals_for(db, user.id)) == len(milestones)

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-03: unknown ids are filtered out silently")
    def test_unknown_milestone_ids_are_rejected(self, client, db, user):
        """
        GOALS-03 — ids matching nothing are dropped with no error, and the
        endpoint returns `201 []`, which is indistinguishable from success.
        """
        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        r = client.post(
            f"/api/goals/from-roadmap/{roadmap.id}",
            json={"milestone_ids": ["does-not-exist"]},
        )

        assert r.status_code in (400, 404)

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-03: cross-roadmap ids are filtered out silently")
    def test_milestones_from_another_roadmap_are_rejected(self, client, db, user):
        """GOALS-03 — cross-roadmap ids fail the same silent way."""
        roadmap_a, _pa, _ma = make_roadmap_with_milestones(db, user.id)
        _roadmap_b, _pb, milestones_b = make_roadmap_with_milestones(db, user.id)

        r = client.post(
            f"/api/goals/from-roadmap/{roadmap_a.id}",
            json={"milestone_ids": [milestones_b[0].id]},
        )

        assert r.status_code in (400, 404)

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-04: _VALID_STATUSES is an unordered set")
    def test_invalid_status_message_has_stable_ordering(self, client):
        """
        GOALS-04 — the detail string is built by joining a *set*, so the order
        of the four statuses changes between interpreter restarts
        (PYTHONHASHSEED). The message is part of the public contract, so
        clients, docs, and snapshot tests cannot rely on it.
        """
        from app.modules.goals.route import _VALID_STATUSES

        detail = client.get("/api/goals", params={"status": "bogus"}).json()["detail"]
        listed = detail.split("Must be one of: ")[1].split(", ")

        assert sorted(listed) == ["completed", "in_progress", "not_started", "paused"]
        assert not isinstance(_VALID_STATUSES, set)

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-05: notification gated on request, not transition")
    def test_recompleting_a_goal_does_not_renotify(self, client, db, user):
        """
        GOALS-05 — the notification fires on the *requested* status rather than
        on an actual transition, so any client that PATCHes the whole object on
        save re-notifies on every edit to an already-completed goal.
        """
        goal = make_goal(db, user.id, status="in_progress")

        client.patch(f"/api/goals/{goal.id}", json={"status": "completed"})
        client.patch(f"/api/goals/{goal.id}", json={"status": "completed"})
        client.patch(f"/api/goals/{goal.id}", json={"status": "completed"})

        assert len(notifications_for(db, user.id)) == 1

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-06: debug print() left in the request path")
    def test_no_debug_output_is_written_to_stdout(self, client, db, user, capfd):
        """
        GOALS-06 — debug `print()` calls in `goals/route.py` and
        `goals/db_service.py` write ~10 lines per request to stdout, including
        the user id and every milestone title, outside any log-level control.
        """
        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        client.post(f"/api/goals/from-roadmap/{roadmap.id}")

        out = capfd.readouterr().out
        assert "[goals/from-roadmap]" not in out
        assert user.id not in out

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-07: collection route registered as ''")
    def test_trailing_slash_serves_the_collection(self, client):
        """
        GOALS-07 — `/api/goals/` 307-redirects instead of serving. `cover-letter`
        registers `"/"` and behaves the opposite way, so no single trailing-slash
        convention works across the API.
        """
        r = client.get("/api/goals/", follow_redirects=False)

        assert r.status_code == 200
