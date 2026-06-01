from typing import Optional

from app.modules.jobs.providers.jsearch import search_jsearch_jobs
from app.schemas import JobCard


async def search_live_jobs(
    query: str,
    location: Optional[str] = None,
    page: int = 1,
    num_pages: int = 1,
) -> list[JobCard]:
    jobs = await search_jsearch_jobs(
        query=query,
        location=location,
        page=page,
        num_pages=num_pages,
    )

    return jobs