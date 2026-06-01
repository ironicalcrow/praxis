from typing import Optional

from app.modules.jobs.providers.jsearch import (
    get_jsearch_job_detail,
    search_jsearch_jobs,
)
from app.schemas import JobCard, JobDetailResponse


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
    country: str = "us",
) -> JobDetailResponse:
    return await get_jsearch_job_detail(
        job_id=job_id,
        country=country,
    )