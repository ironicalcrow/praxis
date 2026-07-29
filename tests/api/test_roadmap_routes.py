"""
HTTP-layer tests for `app/modules/roadmap/route.py` (6 endpoints).

The two generate endpoints delegate to `roadmap_service.generate_from_*`, which
call an LLM and (for `/from-job`) read the `jobs` table — a table carrying a
pgvector column SQLite cannot create. Since the scope here is the *router*, those
service calls are patched, and the tests assert what the route does with the
result: status code, error mapping, notification dispatch, and response shape.

Tests marked `@pytest.mark.bug` assert the behaviour the code SHOULD have and
carry `xfail(strict=True)`, so they report as `xfailed` rather than passing. Each
names its BUG_REPORT.md id. Fixing the bug turns one into an XPASS, which
`strict` escalates to a hard failure — the prompt to drop the marker.
"""

import pytest
from fastapi import HTTPException

from helpers import (
    MISSING_UUID,
    make_milestone,
    make_phase,
    make_roadmap,
    make_roadmap_with_milestones,
    notifications_for,
)

pytestmark = pytest.mark.api


@pytest.fixture
def patch_generate(monkeypatch, db):
    """
    Replace a `roadmap_service.generate_*` coroutine.

    Call with `roadmap=<Roadmap>` to succeed, or `raises=<Exception>` to fail.
    Patching the module the route imported (`app.modules.roadmap.service`) is
    what takes effect, since the route holds a module reference, not a function
    reference.
    """
    import app.modules.roadmap.service as svc

    def _patch(name: str, roadmap=None, raises=None):
        async def _fake(*args, **kwargs):
            if raises is not None:
                raise raises
            return roadmap

        monkeypatch.setattr(svc, name, _fake)

    return _patch


# ── POST /api/roadmap/manual ───────────────────────────────────────────────────

class TestCreateManualRoadmap:
    def test_a_manual_roadmap_is_created_with_201(self, client):
        r = client.post("/api/roadmap/manual", json={"title": "Learn Go"})

        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Learn Go"
        assert body["source_type"] == "manual"
        assert body["source_id"] is None

    def test_the_description_is_persisted(self, client):
        r = client.post(
            "/api/roadmap/manual",
            json={"title": "Learn Go", "description": "From zero to service"},
        )

        assert r.json()["description"] == "From zero to service"

    def test_the_roadmap_is_owned_by_the_authenticated_user(self, client, user):
        r = client.post("/api/roadmap/manual", json={"title": "Mine"})

        assert r.json()["user_id"] == user.id

    def test_a_manual_roadmap_starts_with_no_phases(self, client):
        created = client.post("/api/roadmap/manual", json={"title": "Empty"}).json()

        detail = client.get(f"/api/roadmap/{created['id']}").json()

        assert detail["phases"] == []

    def test_a_missing_title_is_rejected(self, client):
        r = client.post("/api/roadmap/manual", json={"description": "no title"})

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.post("/api/roadmap/manual", json={"title": "Sneaky"})

        assert r.status_code in (401, 403)


# ── POST /api/roadmap/from-conversation ────────────────────────────────────────

class TestGenerateFromConversation:
    def test_a_generated_roadmap_returns_201_with_a_preview(self, client, db, user, patch_generate):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)
        patch_generate("generate_from_conversation", roadmap=roadmap)

        r = client.post("/api/roadmap/from-conversation", json={"conversation_id": "conv-1"})

        assert r.status_code == 201
        body = r.json()
        assert body["roadmap"]["id"] == roadmap.id
        assert len(body["suggested_goals"]) == len(milestones)

    def test_every_milestone_becomes_a_suggested_goal(self, client, db, user, patch_generate):
        roadmap, phase, milestones = make_roadmap_with_milestones(db, user.id)
        patch_generate("generate_from_conversation", roadmap=roadmap)

        body = client.post(
            "/api/roadmap/from-conversation", json={"conversation_id": "conv-1"}
        ).json()

        suggested = body["suggested_goals"]
        assert {g["title"] for g in suggested} == {m.title for m in milestones}
        assert all(g["phase_title"] == phase.title for g in suggested)
        assert {g["milestone_id"] for g in suggested} == {m.id for m in milestones}

    def test_a_missing_conversation_is_404(self, client, patch_generate):
        patch_generate("generate_from_conversation", raises=ValueError("Conversation not found"))

        r = client.post("/api/roadmap/from-conversation", json={"conversation_id": "nope"})

        assert r.status_code == 404
        assert r.json()["detail"] == "Conversation not found"

    def test_an_llm_failure_is_500(self, client, patch_generate):
        patch_generate("generate_from_conversation", raises=RuntimeError("provider exploded"))

        r = client.post("/api/roadmap/from-conversation", json={"conversation_id": "conv-1"})

        assert r.status_code == 500
        assert "Roadmap generation failed" in r.json()["detail"]

    def test_a_missing_conversation_id_is_422(self, client):
        r = client.post("/api/roadmap/from-conversation", json={})

        assert r.status_code == 422

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.post("/api/roadmap/from-conversation", json={"conversation_id": "c"})

        assert r.status_code in (401, 403)


# ── POST /api/roadmap/from-job ─────────────────────────────────────────────────

class TestGenerateFromJob:
    def test_a_generated_roadmap_returns_201_with_a_preview(self, client, db, user, patch_generate):
        roadmap, _phase, milestones = make_roadmap_with_milestones(db, user.id)
        patch_generate("generate_from_job", roadmap=roadmap)

        r = client.post("/api/roadmap/from-job", json={"job_id": "job-1"})

        assert r.status_code == 201
        assert r.json()["roadmap"]["id"] == roadmap.id
        assert len(r.json()["suggested_goals"]) == len(milestones)

    def test_a_missing_job_is_404(self, client, patch_generate):
        patch_generate("generate_from_job", raises=ValueError("Job not found"))

        r = client.post("/api/roadmap/from-job", json={"job_id": MISSING_UUID})

        assert r.status_code == 404
        assert r.json()["detail"] == "Job not found"

    def test_an_llm_failure_is_500(self, client, patch_generate):
        patch_generate("generate_from_job", raises=RuntimeError("provider exploded"))

        r = client.post("/api/roadmap/from-job", json={"job_id": "job-1"})

        assert r.status_code == 500

    def test_a_missing_job_id_is_422(self, client):
        r = client.post("/api/roadmap/from-job", json={})

        assert r.status_code == 422

    def test_a_roadmap_with_no_phases_yields_no_suggested_goals(
        self, client, db, user, patch_generate
    ):
        roadmap = make_roadmap(db, user.id)
        patch_generate("generate_from_job", roadmap=roadmap)

        body = client.post("/api/roadmap/from-job", json={"job_id": "job-1"}).json()

        assert body["suggested_goals"] == []

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.post("/api/roadmap/from-job", json={"job_id": "j"})

        assert r.status_code in (401, 403)


# ── GET /api/roadmap ───────────────────────────────────────────────────────────

class TestListRoadmaps:
    def test_no_roadmaps_returns_an_empty_list(self, client):
        r = client.get("/api/roadmap")

        assert r.status_code == 200
        assert r.json() == []

    def test_roadmaps_are_returned_for_the_authenticated_user(self, client, db, user):
        make_roadmap(db, user.id, title="First")
        make_roadmap(db, user.id, title="Second")

        r = client.get("/api/roadmap")

        assert {rm["title"] for rm in r.json()} == {"First", "Second"}

    def test_another_users_roadmaps_are_not_visible(self, client, db, user, other_user):
        make_roadmap(db, user.id, title="Mine")
        make_roadmap(db, other_user.id, title="Theirs")

        r = client.get("/api/roadmap")

        assert [rm["title"] for rm in r.json()] == ["Mine"]

    def test_the_list_shape_omits_phases(self, client, db, user):
        make_roadmap_with_milestones(db, user.id)

        body = client.get("/api/roadmap").json()

        assert "phases" not in body[0]

    def test_an_anonymous_caller_is_rejected(self, anon_client):
        r = anon_client.get("/api/roadmap")

        assert r.status_code in (401, 403)


# ── GET /api/roadmap/{roadmap_id} ──────────────────────────────────────────────

class TestGetRoadmap:
    def test_the_full_nested_tree_is_returned(self, client, db, user):
        roadmap, phase, milestones = make_roadmap_with_milestones(db, user.id)

        r = client.get(f"/api/roadmap/{roadmap.id}")

        assert r.status_code == 200
        body = r.json()
        assert len(body["phases"]) == 1
        assert body["phases"][0]["title"] == phase.title
        assert len(body["phases"][0]["milestones"]) == len(milestones)

    def test_phases_are_ordered_by_index(self, client, db, user):
        roadmap = make_roadmap(db, user.id)
        make_phase(db, roadmap.id, title="Third", order_index=2)
        make_phase(db, roadmap.id, title="First", order_index=0)
        make_phase(db, roadmap.id, title="Second", order_index=1)

        body = client.get(f"/api/roadmap/{roadmap.id}").json()

        assert [p["title"] for p in body["phases"]] == ["First", "Second", "Third"]

    def test_milestones_are_ordered_by_index(self, client, db, user):
        roadmap = make_roadmap(db, user.id)
        phase = make_phase(db, roadmap.id)
        make_milestone(db, phase.id, title="Last", order_index=2)
        make_milestone(db, phase.id, title="Middle", order_index=1)
        make_milestone(db, phase.id, title="Head", order_index=0)

        body = client.get(f"/api/roadmap/{roadmap.id}").json()

        assert [m["title"] for m in body["phases"][0]["milestones"]] == [
            "Head", "Middle", "Last",
        ]

    def test_an_unknown_roadmap_is_404(self, client):
        r = client.get(f"/api/roadmap/{MISSING_UUID}")

        assert r.status_code == 404
        assert r.json()["detail"] == "Roadmap not found"

    def test_another_users_roadmap_is_404(self, client, db, other_user):
        roadmap = make_roadmap(db, other_user.id)

        r = client.get(f"/api/roadmap/{roadmap.id}")

        assert r.status_code == 404

    def test_a_non_uuid_roadmap_id_is_422(self, client):
        r = client.get("/api/roadmap/not-a-uuid")

        assert r.status_code == 422


# ── DELETE /api/roadmap/{roadmap_id} ───────────────────────────────────────────

class TestDeleteRoadmap:
    def test_a_roadmap_is_deleted_with_204_and_no_body(self, client, db, user):
        roadmap = make_roadmap(db, user.id)

        r = client.delete(f"/api/roadmap/{roadmap.id}")

        assert r.status_code == 204
        assert r.content == b""
        assert client.get("/api/roadmap").json() == []

    def test_deleting_cascades_to_phases_and_milestones(self, client, db, user):
        from app.modules.roadmap.models import RoadmapMilestone, RoadmapPhase

        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        client.delete(f"/api/roadmap/{roadmap.id}")

        db.expire_all()
        assert db.query(RoadmapPhase).count() == 0
        assert db.query(RoadmapMilestone).count() == 0

    def test_an_unknown_roadmap_is_404(self, client):
        r = client.delete(f"/api/roadmap/{MISSING_UUID}")

        assert r.status_code == 404

    def test_another_users_roadmap_cannot_be_deleted(self, client, db, other_user):
        roadmap = make_roadmap(db, other_user.id)

        r = client.delete(f"/api/roadmap/{roadmap.id}")

        assert r.status_code == 404
        assert db.query(type(roadmap)).count() == 1

    def test_a_second_delete_is_404(self, client, db, user):
        roadmap = make_roadmap(db, user.id)

        client.delete(f"/api/roadmap/{roadmap.id}")
        r = client.delete(f"/api/roadmap/{roadmap.id}")

        assert r.status_code == 404


# ── Bug reproductions ──────────────────────────────────────────────────────────

class TestKnownBugs:
    """
    Each test asserts the behaviour the endpoint SHOULD have, and is marked
    `xfail(strict=True)` because it does not have it yet. See the note in
    `test_goals_routes.py` and `tests/README.md`.
    """

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="ROADMAP-01: bare except also catches HTTPException")
    def test_an_http_exception_from_the_service_keeps_its_status(self, client, patch_generate):
        """
        ROADMAP-01 — `route.py:36,61` catch bare `Exception` after `ValueError`.
        `HTTPException` is an `Exception`, so a deliberate 401/403/404 raised
        inside the service is swallowed and re-reported as 500, with the real
        status left only as text inside `detail`.

        Currently latent: no service path raises `HTTPException` today, so the
        reproduction patches one in.
        """
        patch_generate(
            "generate_from_conversation",
            raises=HTTPException(status_code=403, detail="CV belongs to another user"),
        )

        r = client.post("/api/roadmap/from-conversation", json={"conversation_id": "c"})

        assert r.status_code == 403

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="ROADMAP-02: no response_model on the generate endpoints")
    def test_generate_endpoints_declare_a_response_model(self, client):
        """
        ROADMAP-02 — `route.py:24,49` declare only `status_code=201`.
        `RoadmapInsightPreview` exists in schemas.py and documents the shape, but
        is never attached — so the response is unvalidated and OpenAPI documents
        the 201 body as an empty schema.
        """
        schema = client.get("/openapi.json").json()

        for path in ("/api/roadmap/from-conversation", "/api/roadmap/from-job"):
            content = (
                schema["paths"][path]["post"]["responses"]["201"]
                .get("content", {}).get("application/json", {})
            )
            assert content.get("schema"), f"{path} has no declared 201 schema"

    @pytest.mark.bug
    @pytest.mark.xfail(strict=True, reason="GOALS-07: collection route registered as ''")
    def test_trailing_slash_serves_the_collection(self, client):
        """GOALS-07 — same defect as the goals router: `/api/roadmap/` 307s."""
        r = client.get("/api/roadmap/", follow_redirects=False)

        assert r.status_code == 200
