from fastapi import HTTPException

from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.fit_score.scorer import compute_fit_score
from app.modules.jobs.controller import get_job_detail
from app.modules.jobs.services.job_profile_extreactor import (
    extract_job_requirement_profile,
)
from app.schemas import (
    ResumeSchema,
    JobDetailWithFitResponse,
)


async def calculate_job_fit_score(
    job_id: str,
    current_user,
) -> JobDetailWithFitResponse:
    try:
        resume_data = fetch_resume_from_db(str(current_user.id))
        candidate_resume = ResumeSchema(**resume_data)

        job = await get_job_detail(job_id=job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        profile = await extract_job_requirement_profile(job)

        fit_score = await compute_fit_score(
            profile=profile,
            candidate=candidate_resume,
            add_reasoning=True,
        )

        return JobDetailWithFitResponse(
            job=job,
            job_requirement_profile=profile,
            fit_score=fit_score,
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate job fit score: {str(e)}",
        )