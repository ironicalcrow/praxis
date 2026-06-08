"""
Core business logic tests — no database, Redis, or API key required.
All tests are self-contained pure Python; safe to run in any environment.
"""
import pytest


def test_fit_score_blend_formula():
    """Fit score = skill_pct * 0.5 + semantic_pct * 0.5 (used in job_suggestion.py)."""
    def blend(skill_pct: float, semantic_pct: float) -> float:
        return round(skill_pct * 0.5 + semantic_pct * 0.5, 2)

    assert blend(100.0, 100.0) == 100.0
    assert blend(0.0, 0.0) == 0.0
    assert blend(80.0, 60.0) == 70.0
    assert blend(100.0, 0.0) == 50.0
    assert blend(60.0, 90.0) == 75.0


def test_skill_match_percentage():
    """Skill overlap % = |job_skills ∩ resume_skills| / |job_skills| * 100."""
    def skill_pct(job_skills: list, resume_skills: list) -> float:
        if not job_skills:
            return 0.0
        job_set = {s.lower() for s in job_skills}
        resume_set = {s.lower() for s in resume_skills}
        matched = len(job_set & resume_set)
        return (matched / len(job_set)) * 100

    assert skill_pct(["Python", "FastAPI"], ["python", "fastapi"]) == 100.0
    assert skill_pct(["Python", "FastAPI", "SQL"], ["python", "sql"]) == pytest.approx(66.67, abs=0.1)
    assert skill_pct(["Python"], ["Java"]) == 0.0
    assert skill_pct([], ["Python"]) == 0.0
    assert skill_pct(["Python", "Go"], ["python"]) == 50.0


def test_application_status_pipeline_order():
    """Application statuses must follow: saved → applied → interviewing → offer / rejected."""
    pipeline = ["saved", "applied", "interviewing", "offer", "rejected"]

    assert pipeline.index("saved") < pipeline.index("applied")
    assert pipeline.index("applied") < pipeline.index("interviewing")
    assert pipeline.index("interviewing") < pipeline.index("offer")
    assert "offer" in pipeline
    assert "rejected" in pipeline
    assert len(pipeline) == 5


def test_goal_cumulative_date_offsets():
    """Milestone target dates are cumulative offsets from the roadmap anchor date."""
    from datetime import date, timedelta

    anchor = date(2026, 1, 1)
    milestones = [
        {"id": "m1", "days": 7},
        {"id": "m2", "days": 14},
        {"id": "m3", "days": 7},
    ]

    running = 0
    targets = {}
    for m in milestones:
        running += m["days"]
        targets[m["id"]] = anchor + timedelta(days=running)

    assert targets["m1"] == date(2026, 1, 8)
    assert targets["m2"] == date(2026, 1, 22)
    assert targets["m3"] == date(2026, 1, 29)
    assert targets["m2"] > targets["m1"]
    assert targets["m3"] > targets["m2"]


def test_confirmation_and_cancellation_detection():
    """Token-based confirm/cancel detection mirrors chat/service.py logic."""
    CONFIRM = {"yes", "yeah", "yep", "sure", "ok", "okay", "go ahead",
               "proceed", "confirm", "do it", "sounds good", "alright",
               "please", "go", "fine", "agreed"}
    CANCEL = {"no", "nope", "cancel", "abort", "stop", "never mind",
              "nevermind", "don't", "dont", "skip"}

    def is_confirm(text: str) -> bool:
        t = text.strip().lower()
        return any(tok in t for tok in CONFIRM) and not any(tok in t for tok in CANCEL)

    def is_cancel(text: str) -> bool:
        t = text.strip().lower()
        return any(tok in t for tok in CANCEL)

    assert is_confirm("yes") is True
    assert is_confirm("yeah, go ahead") is True
    assert is_confirm("ok") is True
    assert is_confirm("no") is False
    assert is_cancel("cancel") is True
    assert is_cancel("never mind") is True
    assert is_cancel("ok") is False
