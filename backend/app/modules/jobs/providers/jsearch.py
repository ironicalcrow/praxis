from typing import Any,Optional

import httpx

from app.core.config import settings
from app.schemas import JobCard

class JSearchError(Exception):
    pass

def build_search_query(query:str,location:Optional[str]=None)->str:
    if location:
        return f"{query} in {location}"
    return query

def format_salary(job: dict[str, Any]) -> Optional[str]:
    min_salary = job.get("job_min_salary")
    max_salary = job.get("job_max_salary")
    currency = job.get("job_salary_currency")
    period = job.get("job_salary_period")

    if min_salary and max_salary:
        salary = f"{min_salary} - {max_salary}"
    elif min_salary:
        salary = f"{min_salary}+"
    else:
        return None

    if currency:
        salary = f"{currency} {salary}"

    if period:
        salary = f"{salary}/{period.lower()}"

    return salary

def normalize_job(job: dict[str, Any]) -> JobCard:
    city = job.get("job_city")
    state = job.get("job_state")
    country = job.get("job_country")

    location_parts = [part for part in [city, state, country] if part]
    location = ", ".join(location_parts) if location_parts else job.get("job_location")

    return JobCard(
        external_id=job.get("job_id"),
        title=job.get("job_title") or "Untitled Role",
        company=job.get("employer_name"),
        location=location,
        employment_type=job.get("job_employment_type"),
        salary_range=format_salary(job),
        deadline=None,
        description=job.get("job_description"),
        job_url=job.get("job_apply_link") or job.get("job_google_link"),
        source="jsearch",
        posted_at=job.get("job_posted_at_datetime_utc") or job.get("job_posted_at"),
    )

async def search_jsearch_jobs(
    query: str,
    location: Optional[str] = None,
    page: int = 1,
    num_pages: int = 1,
) -> list[JobCard]:
    if not settings.JSEARCH_API_KEY:
        raise JSearchError("JSEARCH_API_KEY is missing in .env")

    url = settings.jsearch_URL

    headers = {
        "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
        "X-RapidAPI-Host": settings.JSEARCH_API_HOST,
    }

    params = {
        "query": build_search_query(query, location),
        "page": str(page),
        "num_pages": str(num_pages),
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise JSearchError(
            f"JSearch API error {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        raise JSearchError(
            f"Could not connect to JSearch API. "
            f"Error type: {type(e).__name__}. "
            f"Error: {repr(e)}"
        )

    data = response.json()
    raw_jobs = data.get("data", [])

    return [normalize_job(job) for job in raw_jobs]