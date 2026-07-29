"""
Cross-module integration flows: roadmap → goals → notifications.

The per-router files test each endpoint in isolation. These tests follow the
journey a real user takes, and cover the seams between the three modules — which
is where the state actually goes wrong.

Tests marked `@pytest.mark.bug` assert the behaviour the code SHOULD have and
carry `xfail(strict=True)`, so they report as `xfailed` rather than passing. Each
names its BUG_REPORT.md id. Fixing the bug turns one into an XPASS, which
`strict` escalates to a hard failure — the prompt to drop the marker.
"""

import pytest

from helpers import make_milestone, make_phase, make_roadmap, notifications_for

pytestmark = pytest.mark.flow


def build_roadmap_via_api(client, db, user, milestone_titles=None):
    """
    Create a roadmap through the API, then attach phases/milestones directly.

    The generate endpoints need an LLM, and `/manual` deliberately creates an
    empty roadmap (`route.py:87` passes `phases_data=[]`), so the tree is seeded
    at the db layer — the part under test here is what *goals* does with it.
    """
    created = client.post(
        "/api/roadmap/manual",
        json={"title": "Backend Engineer", "description": "Six month plan"},
    ).json()

    phase = make_phase(db, created["id"], title="Foundations")
    titles = milestone_titles or ["Learn SQL", "Build an API", "Deploy it"]
    milestones = [
        make_milestone(db, phase.id, title=t, order_index=i, estimated_days=7)
        for i, t in enumerate(titles)
    ]
    return created, phase, milestones


# ── The happy path, end to end ─────────────────────────────────────────────────

class TestRoadmapToGoalsJourney:
    def test_the_full_journey(self, client, db, user):
        """manual roadmap → seed tree → promote → track → complete."""
        roadmap, _phase, milestones = build_roadmap_via_api(client, db, user)

        # The roadmap is visible with its full tree
        detail = client.get(f"/api/roadmap/{roadmap['id']}").json()
        assert len(detail["phases"][0]["milestones"]) == 3

        # Promote every milestone to a goal
        goals = client.post(f"/api/goals/from-roadmap/{roadmap['id']}").json()
        assert len(goals) == len(milestones)

        # They show up in the goal tracker, linked back to the roadmap
        listed = client.get("/api/goals").json()
        assert len(listed) == 3
        assert all(g["roadmap_id"] == roadmap["id"] for g in listed)
        assert all(g["source_type"] == "roadmap" for g in listed)

        # Work one of them through its lifecycle
        first = listed[0]
        assert client.patch(
            f"/api/goals/{first['id']}", json={"status": "in_progress"}
        ).json()["status"] == "in_progress"
        assert client.patch(
            f"/api/goals/{first['id']}", json={"status": "completed"}
        ).json()["status"] == "completed"

        # Filtering reflects the new state
        assert len(client.get("/api/goals", params={"status": "completed"}).json()) == 1
        assert len(client.get("/api/goals", params={"status": "not_started"}).json()) == 2

    def test_promotion_and_completion_both_notify(self, client, db, user):
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)

        client.post(f"/api/goals/from-roadmap/{roadmap['id']}")
        goal = client.get("/api/goals").json()[0]
        client.patch(f"/api/goals/{goal['id']}", json={"status": "completed"})

        types_seen = [n.type for n in notifications_for(db, user.id)]
        assert "goals_created_from_roadmap" in types_seen
        assert "goal_completed" in types_seen

    def test_notifications_from_the_flow_are_readable_and_dismissable(
        self, client, db, user
    ):
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{roadmap['id']}")

        inbox = client.get("/api/notifications").json()
        assert len(inbox) == 1

        # Read it, then confirm it drops out of the unread filter
        assert client.patch(f"/api/notifications/{inbox[0]['id']}/read").json()["is_read"] is True
        assert client.get("/api/notifications", params={"unread_only": True}).json() == []

        # And can be deleted
        assert client.delete(f"/api/notifications/{inbox[0]['id']}").status_code == 204
        assert client.get("/api/notifications").json() == []

    def test_partial_promotion_then_promoting_the_rest(self, client, db, user):
        roadmap, _phase, milestones = build_roadmap_via_api(client, db, user)

        client.post(
            f"/api/goals/from-roadmap/{roadmap['id']}",
            json={"milestone_ids": [milestones[0].id]},
        )
        assert len(client.get("/api/goals").json()) == 1

        client.post(
            f"/api/goals/from-roadmap/{roadmap['id']}",
            json={"milestone_ids": [milestones[1].id, milestones[2].id]},
        )

        listed = client.get("/api/goals").json()
        assert len(listed) == 3
        assert {g["title"] for g in listed} == {m.title for m in milestones}

    def test_target_dates_accumulate_across_the_promoted_milestones(
        self, client, db, user
    ):
        """Each milestone's deadline stacks on the previous one's estimate."""
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)

        goals = client.post(f"/api/goals/from-roadmap/{roadmap['id']}").json()

        dates = [g["target_date"] for g in goals]
        assert all(d is not None for d in dates)
        assert dates == sorted(dates)
        assert len(set(dates)) == 3  # 7, 14, 21 days out — not all the same


# ── Isolation between users ────────────────────────────────────────────────────

class TestCrossUserIsolation:
    def test_the_whole_flow_is_scoped_to_its_owner(self, client, db, user, other_user):
        mine, _p, _m = build_roadmap_via_api(client, db, user)

        theirs = make_roadmap(db, other_user.id, title="Theirs")
        their_phase = make_phase(db, theirs.id)
        make_milestone(db, their_phase.id, title="Their milestone")

        client.post(f"/api/goals/from-roadmap/{mine['id']}")

        # Only my roadmap and my goals are visible
        assert [r["title"] for r in client.get("/api/roadmap").json()] == ["Backend Engineer"]
        assert all(g["roadmap_id"] == mine["id"] for g in client.get("/api/goals").json())

        # And theirs is untouchable
        assert client.get(f"/api/roadmap/{theirs.id}").status_code == 404
        assert client.post(f"/api/goals/from-roadmap/{theirs.id}").status_code == 404
        assert client.delete(f"/api/roadmap/{theirs.id}").status_code == 404

    def test_notifications_do_not_leak_between_users(
        self, client, as_user, db, user, other_user
    ):
        mine, _p, _m = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{mine['id']}")

        assert len(as_user(other_user).get("/api/notifications").json()) == 0
        assert len(as_user(user).get("/api/notifications").json()) == 1


# ── Bug reproductions ──────────────────────────────────────────────────────────

class TestKnownBugs:
    """
    Each test asserts the behaviour the system SHOULD have, and is marked
    `xfail(strict=True)` because it does not have it yet. See `tests/README.md`.
    """

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="ROADMAP-03: Roadmap.goals declares no cascade")
    def test_deleting_a_roadmap_leaves_no_orphaned_goals(self, client, db, user):
        """
        ROADMAP-03 — `Roadmap.phases` declares `cascade="all, delete-orphan"` but
        `Roadmap.goals` (`models.py:33`) declares none. Deleting a roadmap
        destroys the phases and milestones while leaving the goals behind with
        their foreign keys nulled and `source_type` untouched.

        The result is a row that contradicts itself: it claims a roadmap origin
        while being unable to name one, and the milestone that defined it is
        gone.

        Any of these would be correct — cascade-delete the goals, block the
        delete while goals exist, or rewrite `source_type` to "manual". This
        asserts the last, since the goals represent the user's own work and
        deleting them silently would be worse.
        """
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{roadmap['id']}")

        assert client.delete(f"/api/roadmap/{roadmap['id']}").status_code == 204

        for g in client.get("/api/goals").json():
            assert not (g["source_type"] == "roadmap" and g["roadmap_id"] is None), (
                "goal claims a roadmap origin it cannot name"
            )

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="ROADMAP-03: orphans cannot be re-linked")
    def test_re_promoting_after_a_delete_does_not_duplicate(self, client, db, user):
        """
        ROADMAP-03 — there is no recovery path. Rebuilding the roadmap mints new
        milestone ids, so re-promoting creates a *second* set of goals rather
        than reattaching the orphans (compounding GOALS-02), leaving the user
        with duplicate titles to clean up by hand.
        """
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{roadmap['id']}")
        client.delete(f"/api/roadmap/{roadmap['id']}")

        rebuilt, _p2, _m2 = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{rebuilt['id']}")

        assert len(client.get("/api/goals").json()) == 3

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="ROADMAP-03: completion loses its provenance")
    def test_a_completed_goal_keeps_its_provenance(self, client, db, user):
        """
        ROADMAP-03 — progress is not protected. A goal the user has already
        completed keeps its `completed` status but loses every reference to the
        work it came from, so the roadmap's completion history cannot be
        reconstructed.
        """
        roadmap, _phase, _milestones = build_roadmap_via_api(client, db, user)
        client.post(f"/api/goals/from-roadmap/{roadmap['id']}")
        goal = client.get("/api/goals").json()[0]
        client.patch(f"/api/goals/{goal['id']}", json={"status": "completed"})

        client.delete(f"/api/roadmap/{roadmap['id']}")

        after = [g for g in client.get("/api/goals").json() if g["id"] == goal["id"]][0]
        assert after["status"] == "completed"
        assert after["roadmap_id"] is not None
