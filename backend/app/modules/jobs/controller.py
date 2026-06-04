from typing import Optional

from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.jobs.providers.jsearch import (
    get_jsearch_job_detail,
    search_jsearch_jobs,
)
from app.modules.jobs.services.fit_scorer import compute_fit_score
from app.modules.jobs.services.job_profile_extractor import extract_job_requirement_profile
from app.schemas import JobCard, JobDetailResponse, ResumeSchema, FitScoreResponse


async def search_live_jobs(
    query: str,
    location: Optional[str] = None,
    page: int = 1,
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "all",
) -> list[JobCard]:
    return await search_jsearch_jobs(
        query=query,
        location=location,
        page=page,
        num_pages=num_pages,
        country=country,
        date_posted=date_posted,
    )


async def get_job_detail(
    job_id: str,
) -> JobDetailResponse | None:
    job = await get_jsearch_job_detail(
        job_id=job_id,
    )

    if not job:
        return None

    return job


async def calculate_job_fit_score(
    job_id: str,
    current_user,
) -> FitScoreResponse:
    resume_data = fetch_resume_from_db(current_user.id)
    candidate_resume = ResumeSchema(**resume_data)

    job = await get_job_detail(job_id=job_id)

    if not job:
        raise ValueError("Job not found")

    profile = await extract_job_requirement_profile(job)

    fit_score = await compute_fit_score(
        profile=profile,
        candidate=candidate_resume,
        add_reasoning=True,
    )

    return fit_score