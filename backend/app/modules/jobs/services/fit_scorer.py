from typing import Optional

from app.schemas import ResumeSchema, FitScoreResponse, JobRequirementProfile


class FitScoreScorerError(Exception):
    pass


def clamp_fit_score(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return round(value, 2)


def get_verdict(score: float) -> str:
    if score >= 85:
        return "Excellent fit"
    if score >= 70:
        return "Strong fit"
    if score >= 55:
        return "Moderate fit"
    if score >= 40:
        return "Weak fit"
    return "Poor fit"


async def compute_fit_score(
    profile: JobRequirementProfile,
    candidate: ResumeSchema,
    semantic_similarity: Optional[float] = None,
    add_reasoning: bool = True,
) -> FitScoreResponse:
    """
    Blended fit score: skill overlap + semantic similarity (when available).
    - semantic_similarity: cosine similarity from pgvector, range 0.0-1.0.
      When None (e.g. live search, detail view), falls back to skill-only scoring.
    """
    job_skills = set(s.lower().strip() for s in profile.required_skills)
    job_skills.update(s.lower().strip() for s in profile.preferred_skills)
    job_skills.update(s.lower().strip() for s in profile.tools_and_technologies)
    job_skills.update(s.lower().strip() for s in profile.soft_skills)
    job_skills.update(s.lower().strip() for s in profile.qualifications)

    cv_skills = set(s.lower().strip() for s in candidate.skills)

    overlap = cv_skills.intersection(job_skills)
    missing = job_skills - cv_skills

    if len(job_skills) == 0:
        skill_score = 65.0
    else:
        skill_score = (len(overlap) / float(len(job_skills))) * 100.0

    if semantic_similarity is not None:
        # Clamp to [0, 1] defensively
        sem = max(0.0, min(1.0, float(semantic_similarity)))
        semantic_score = sem * 100.0
        score = skill_score * 0.5 + semantic_score * 0.5
        reason = (
            f"Candidate matches {len(overlap)}/{len(job_skills)} required skills "
            f"with {sem * 100:.0f}% semantic alignment."
        )
    else:
        score = skill_score
        reason = f"Candidate matches {len(overlap)} out of {len(job_skills)} required/preferred skills."

    score = clamp_fit_score(score)
    verdict = get_verdict(score)

    if not add_reasoning:
        return FitScoreResponse(
            fit_score=score,
            verdict=verdict,
            strengths=[],
            weaknesses=[],
            reason="Reasoning disabled.",
        )

    strengths = [f"Matches required skill: {s.title()}" for s in overlap][:10]
    weaknesses = [f"Missing required skill: {s.title()}" for s in missing][:10]

    return FitScoreResponse(
        fit_score=score,
        verdict=verdict,
        strengths=strengths,
        weaknesses=weaknesses,
        reason=reason,
    )
