"""
Pydantic contract tests for the goals / roadmap / notifications schemas.

The route tests exercise these indirectly through real requests. This file pins
the schemas directly: which fields are required, what `UUIDStr` accepts and
rejects, and whether `from_attributes` round-trips an ORM row faithfully. Those
are the rules that decide whether a 422 or a 500 reaches the caller, so they are
worth stating once, explicitly.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.modules.goals.schemas import BulkGoalConfirm, GoalCreate, GoalOut, GoalUpdate
from app.modules.notifications.schemas import NotificationOut
from app.modules.roadmap.schemas import (
    GenerateFromConversationRequest,
    GenerateFromJobRequest,
    ManualRoadmapCreate,
    MilestoneOut,
    PhaseOut,
    RoadmapDetailOut,
    RoadmapInsightPreview,
    RoadmapOut,
    SuggestedGoal,
)

from helpers import make_goal, make_notification, make_roadmap_with_milestones

VALID_UUID = "11111111-1111-4111-8111-111111111111"


# ── Goals ──────────────────────────────────────────────────────────────────────

class TestGoalCreate:
    def test_only_the_title_is_required(self):
        g = GoalCreate(title="Learn Rust")

        assert g.title == "Learn Rust"
        assert g.description is None
        assert g.target_date is None

    def test_a_missing_title_is_rejected(self):
        with pytest.raises(ValidationError):
            GoalCreate()

    def test_an_iso_date_string_is_coerced(self):
        assert GoalCreate(title="t", target_date="2026-12-31").target_date == date(2026, 12, 31)

    @pytest.mark.parametrize("bad", ["31-12-2026", "not-a-date", "2026-13-01"])
    def test_malformed_dates_are_rejected(self, bad):
        with pytest.raises(ValidationError):
            GoalCreate(title="t", target_date=bad)

    def test_an_empty_title_is_accepted(self):
        """No `min_length` is declared — documenting that "" reaches the database."""
        assert GoalCreate(title="").title == ""


class TestGoalUpdate:
    def test_every_field_is_optional(self):
        u = GoalUpdate()

        assert (u.title, u.description, u.status, u.target_date) == (None, None, None, None)

    def test_exclude_unset_distinguishes_omitted_from_explicit_null(self):
        """
        The distinction the route throws away. `exclude_unset` keeps an explicit
        null and drops an omitted key; `exclude_none` — what `route.py:114`
        actually uses — cannot tell them apart. This is the mechanism behind
        GOALS-01.
        """
        omitted = GoalUpdate(title="new")
        explicit = GoalUpdate(title="new", target_date=None)

        assert omitted.model_dump(exclude_unset=True) == {"title": "new"}
        assert explicit.model_dump(exclude_unset=True) == {"title": "new", "target_date": None}

        # Both collapse to the same thing under exclude_none:
        assert omitted.model_dump(exclude_none=True) == explicit.model_dump(exclude_none=True)

    def test_status_is_an_unconstrained_string_at_the_schema_layer(self):
        """Validation lives in the route, not the schema — hence 400 rather than 422."""
        assert GoalUpdate(status="nonsense").status == "nonsense"


class TestGoalOut:
    def test_it_round_trips_an_orm_row(self, db, user):
        goal = make_goal(db, user.id, title="From ORM", target_date=date(2026, 6, 1))

        out = GoalOut.model_validate(goal)

        assert out.id == goal.id
        assert out.user_id == user.id
        assert out.title == "From ORM"
        assert out.target_date == date(2026, 6, 1)

    def test_a_uuid_object_user_id_is_coerced_to_a_string(self):
        """`UUIDStr` accepts a UUID instance and normalises it."""
        import uuid as uuid_mod

        out = GoalOut(
            id="g1", user_id=uuid_mod.UUID(VALID_UUID), title="t", status="not_started",
            source_type="manual", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )

        assert out.user_id == VALID_UUID
        assert isinstance(out.user_id, str)

    def test_a_non_uuid_user_id_is_rejected(self):
        with pytest.raises(ValidationError):
            GoalOut(
                id="g1", user_id="not-a-uuid", title="t", status="not_started",
                source_type="manual", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )

    def test_the_id_field_is_a_plain_string_not_a_uuidstr(self):
        """`id` is `str` while `user_id` is `UUIDStr` — an asymmetry worth knowing."""
        out = GoalOut(
            id="literally-anything", user_id=VALID_UUID, title="t", status="not_started",
            source_type="manual", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )

        assert out.id == "literally-anything"

    @pytest.mark.parametrize("missing", ["id", "user_id", "title", "status", "source_type"])
    def test_required_fields(self, missing):
        payload = {
            "id": "g1", "user_id": VALID_UUID, "title": "t", "status": "not_started",
            "source_type": "manual", "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        payload.pop(missing)

        with pytest.raises(ValidationError):
            GoalOut(**payload)


class TestBulkGoalConfirm:
    def test_milestone_ids_defaults_to_none(self):
        assert BulkGoalConfirm().milestone_ids is None

    def test_an_empty_list_is_preserved_as_distinct_from_none(self):
        """The route collapses both to None at `goals/route.py:55`; the schema does not."""
        assert BulkGoalConfirm(milestone_ids=[]).milestone_ids == []

    def test_a_non_list_is_rejected(self):
        with pytest.raises(ValidationError):
            BulkGoalConfirm(milestone_ids="not-a-list")


# ── Roadmap ────────────────────────────────────────────────────────────────────

class TestRoadmapRequestBodies:
    def test_conversation_id_is_required(self):
        assert GenerateFromConversationRequest(conversation_id="c1").conversation_id == "c1"
        with pytest.raises(ValidationError):
            GenerateFromConversationRequest()

    def test_job_id_is_required(self):
        assert GenerateFromJobRequest(job_id="j1").job_id == "j1"
        with pytest.raises(ValidationError):
            GenerateFromJobRequest()

    def test_neither_id_is_validated_as_a_uuid(self):
        """Both are plain `str`, so a malformed id reaches the service as a 404, not a 422."""
        assert GenerateFromJobRequest(job_id="obviously-not-a-uuid").job_id

    def test_manual_roadmap_requires_only_a_title(self):
        m = ManualRoadmapCreate(title="Plan")

        assert m.description is None
        with pytest.raises(ValidationError):
            ManualRoadmapCreate()


class TestRoadmapOut:
    def test_it_round_trips_an_orm_row(self, db, user):
        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        out = RoadmapOut.model_validate(roadmap)

        assert out.id == roadmap.id
        assert out.user_id == user.id
        assert out.source_type == "manual"

    def test_the_list_shape_carries_no_phases(self, db, user):
        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        assert "phases" not in RoadmapOut.model_validate(roadmap).model_dump()

    def test_the_detail_shape_nests_phases_and_milestones(self, db, user):
        roadmap, phase, milestones = make_roadmap_with_milestones(db, user.id)

        out = RoadmapDetailOut.model_validate(roadmap)

        assert len(out.phases) == 1
        assert out.phases[0].title == phase.title
        assert len(out.phases[0].milestones) == len(milestones)

    def test_phases_default_to_empty(self):
        out = RoadmapDetailOut(
            id="r1", user_id=VALID_UUID, title="t", source_type="manual",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )

        assert out.phases == []


class TestMilestoneAndPhaseOut:
    def test_milestone_required_and_optional_fields(self, db, user):
        _roadmap, phase, milestones = make_roadmap_with_milestones(db, user.id)

        out = MilestoneOut.model_validate(milestones[0])

        assert out.phase_id == phase.id
        assert out.order_index == 0
        assert out.resource_url is None

    def test_a_milestone_without_an_order_index_is_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneOut(id="m1", phase_id="p1", title="t")

    def test_phase_milestones_default_to_empty(self):
        assert PhaseOut(id="p1", roadmap_id="r1", title="t", order_index=0).milestones == []


class TestRoadmapInsightPreview:
    def test_the_preview_nests_a_detail_roadmap_and_suggested_goals(self, db, user):
        roadmap, phase, milestones = make_roadmap_with_milestones(db, user.id)

        preview = RoadmapInsightPreview(
            roadmap=RoadmapDetailOut.model_validate(roadmap),
            suggested_goals=[
                SuggestedGoal(
                    title=m.title, description=m.description,
                    milestone_id=m.id, phase_title=phase.title,
                )
                for m in milestones
            ],
        )

        assert len(preview.suggested_goals) == 3
        assert preview.roadmap.id == roadmap.id

    def test_a_suggested_goal_requires_its_milestone_and_phase(self):
        with pytest.raises(ValidationError):
            SuggestedGoal(title="t")

    def test_the_service_output_validates_against_the_declared_schema(self, db, user):
        """
        The shape `build_roadmap_insight_preview` returns *does* satisfy
        `RoadmapInsightPreview` — the schema is simply never attached to the
        route (ROADMAP-02). This shows the fix would be a one-line change, not a
        reshaping job.
        """
        from app.modules.roadmap.service import build_roadmap_insight_preview

        roadmap, _phase, _milestones = make_roadmap_with_milestones(db, user.id)

        preview = build_roadmap_insight_preview(roadmap)

        assert RoadmapInsightPreview.model_validate(preview)


# ── Notifications ──────────────────────────────────────────────────────────────

class TestNotificationOut:
    def test_it_round_trips_an_orm_row(self, db, user):
        n = make_notification(db, user.id, data={"goal_id": "g1"})

        out = NotificationOut.model_validate(n)

        assert out.id == n.id
        assert out.user_id == user.id
        assert out.data == {"goal_id": "g1"}
        assert out.is_read is False

    def test_data_is_optional_and_untyped(self):
        """`Optional[Any]` — a list, a scalar, or null all validate."""
        base = {
            "id": "n1", "user_id": VALID_UUID, "type": "t", "title": "T",
            "message": "m", "is_read": False, "created_at": datetime.utcnow(),
        }

        assert NotificationOut(**base).data is None
        assert NotificationOut(**base, data=[1, 2]).data == [1, 2]
        assert NotificationOut(**base, data="scalar").data == "scalar"

    def test_created_at_is_required(self):
        """
        The schema-side half of NOTIF-05: the column is nullable, this field is
        not, so a NULL row cannot be serialised and the endpoint 500s.
        """
        with pytest.raises(ValidationError):
            NotificationOut(
                id="n1", user_id=VALID_UUID, type="t", title="T", message="m",
                is_read=False, created_at=None,
            )

    def test_user_id_is_a_plain_string_here_unlike_goals(self):
        """`NotificationOut.user_id` is `str`, not `UUIDStr` — no coercion, no rejection."""
        out = NotificationOut(
            id="n1", user_id="not-a-uuid", type="t", title="T", message="m",
            is_read=False, created_at=datetime.utcnow(),
        )

        assert out.user_id == "not-a-uuid"

    @pytest.mark.parametrize("missing", ["id", "user_id", "type", "title", "message", "is_read"])
    def test_required_fields(self, missing):
        payload = {
            "id": "n1", "user_id": VALID_UUID, "type": "t", "title": "T",
            "message": "m", "is_read": False, "created_at": datetime.utcnow(),
        }
        payload.pop(missing)

        with pytest.raises(ValidationError):
            NotificationOut(**payload)
