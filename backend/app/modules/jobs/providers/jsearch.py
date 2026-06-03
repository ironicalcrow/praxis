from typing import Any, Optional

import httpx

from app.core.config import settings
from app.schemas import (
    ApplyOption,
    EmployerReview,
    JobCard,
    JobDetailResponse,
    JobHighlights,
    RequiredExperience,
    SalaryInfo,
)


class JSearchError(Exception):
    pass


def build_search_query(query: str, location: Optional[str] = None) -> str:
    if location:
        return f"{query} in {location}"
    return query


def build_location(job: dict[str, Any]) -> Optional[str]:
    city = job.get("job_city")
    state = job.get("job_state")
    country = job.get("job_country")

    location_parts = [part for part in [city, state, country] if part]

    if location_parts:
        return ", ".join(location_parts)

    return job.get("job_location")


def build_salary(job: dict[str, Any]) -> Optional[SalaryInfo]:
    salary_text = job.get("job_salary")
    min_salary = job.get("job_min_salary")
    max_salary = job.get("job_max_salary")
    currency = job.get("job_salary_currency")
    period = job.get("job_salary_period")

    if not salary_text:
        if min_salary is not None and max_salary is not None:
            salary_text = f"{min_salary} - {max_salary}"
        elif min_salary is not None:
            salary_text = f"{min_salary}+"
        elif max_salary is not None:
            salary_text = f"Up to {max_salary}"

        if salary_text and currency:
            salary_text = f"{currency} {salary_text}"

        if salary_text and period:
            salary_text = f"{salary_text}/{period}"

    if (
        salary_text is None
        and min_salary is None
        and max_salary is None
        and currency is None
        and period is None
    ):
        return None

    return SalaryInfo(
        salary_text=salary_text,
        min_salary=min_salary,
        max_salary=max_salary,
        currency=currency,
        period=period,
    )


def build_description_preview(description: Optional[str], limit: int = 400) -> Optional[str]:
    if not description:
        return None

    clean_description = " ".join(description.split())

    if len(clean_description) <= limit:
        return clean_description

    return clean_description[:limit].rstrip() + "..."


def build_highlights(job: dict[str, Any]) -> JobHighlights:
    highlights = job.get("job_highlights") or {}

    return JobHighlights(
        qualifications=highlights.get("Qualifications") or [],
        responsibilities=highlights.get("Responsibilities") or [],
        benefits=highlights.get("Benefits") or [],
    )


def build_required_experience(job: dict[str, Any]) -> Optional[RequiredExperience]:
    required_experience = job.get("job_required_experience")

    if not required_experience:
        return None

    return RequiredExperience(
        no_experience_required=required_experience.get("no_experience_required"),
        required_experience_in_months=required_experience.get(
            "required_experience_in_months"
        ),
        experience_mentioned=required_experience.get("experience_mentioned"),
        experience_preferred=required_experience.get("experience_preferred"),
    )


def build_apply_options(job: dict[str, Any]) -> list[ApplyOption]:
    raw_options = job.get("apply_options") or []

    return [
        ApplyOption(
            publisher=item.get("publisher"),
            apply_link=item.get("apply_link"),
            is_direct=item.get("is_direct"),
        )
        for item in raw_options
    ]


def build_employer_reviews(job: dict[str, Any]) -> list[EmployerReview]:
    raw_reviews = job.get("employer_reviews") or []

    return [
        EmployerReview(
            publisher=item.get("publisher"),
            employer_name=item.get("employer_name"),
            score=item.get("score"),
            num_stars=item.get("num_stars"),
            review_count=item.get("review_count"),
            max_score=item.get("max_score"),
            reviews_link=item.get("reviews_link"),
        )
        for item in raw_reviews
    ]


def normalize_job_card(job: dict[str, Any]) -> JobCard:
    card = JobCard(
        external_id=job.get("job_id"),
        title=job.get("job_title") or "Untitled Role",
        company=job.get("employer_name"),
        company_logo=job.get("employer_logo"),
        company_website=job.get("employer_website"),
        publisher=job.get("job_publisher"),
        employment_type=job.get("job_employment_type_text")
        or job.get("job_employment_type"),
        employment_types=job.get("job_employment_types") or [],
        location=build_location(job),
        city=job.get("job_city"),
        state=job.get("job_state"),
        country=job.get("job_country"),
        is_remote=job.get("job_is_remote"),
        apply_url=job.get("job_apply_link") or job.get("job_google_link"),
        is_direct_apply=job.get("job_apply_is_direct"),
        description_preview=build_description_preview(job.get("job_description")),
        posted_at=job.get("job_posted_at_datetime_utc"),
        posted_human_readable=job.get("job_posted_human_readable")
        or job.get("job_posted_at"),
        deadline=job.get("job_offer_expiration_datetime_utc"),
        salary=build_salary(job),
        source="jsearch",
    )

    card.set_raw_payload(job)
    return card


def normalize_job_detail(job: dict[str, Any]) -> JobDetailResponse:
    detail = JobDetailResponse(
        external_id=job.get("job_id"),
        title=job.get("job_title") or "Untitled Role",
        company=job.get("employer_name"),
        company_logo=job.get("employer_logo"),
        company_website=job.get("employer_website"),
        publisher=job.get("job_publisher"),
        employment_type=job.get("job_employment_type_text")
        or job.get("job_employment_type"),
        employment_types=job.get("job_employment_types") or [],
        location=build_location(job),
        city=job.get("job_city"),
        state=job.get("job_state"),
        country=job.get("job_country"),
        latitude=job.get("job_latitude"),
        longitude=job.get("job_longitude"),
        is_remote=job.get("job_is_remote"),
        work_arrangement=job.get("work_arrangement"),
        apply_url=job.get("job_apply_link") or job.get("job_google_link"),
        is_direct_apply=job.get("job_apply_is_direct"),
        apply_options=build_apply_options(job),
        description=job.get("job_description"),
        posted_at=job.get("job_posted_at_datetime_utc"),
        posted_human_readable=job.get("job_posted_human_readable")
        or job.get("job_posted_at"),
        deadline=job.get("job_offer_expiration_datetime_utc"),
        salary=build_salary(job),
        benefits=job.get("job_benefits") or [],
        benefits_extended=job.get("benefits_extended") or [],
        highlights=build_highlights(job),
        required_experience=build_required_experience(job),
        seniority_level=job.get("seniority_level"),
        required_experience_years=job.get("required_experience_years"),
        required_technologies=job.get("required_technologies") or [],
        preferred_technologies=job.get("preferred_technologies") or [],
        methodologies=job.get("methodologies") or [],
        soft_skills=job.get("soft_skills") or [],
        industry=job.get("industry"),
        job_function=job.get("job_function"),
        ai_ml_involved=job.get("ai_ml_involved"),
        has_management_responsibilities=job.get("has_management_responsibilities"),
        employer_reviews=build_employer_reviews(job),
        source="jsearch",
    )

    detail.set_raw_payload(job)
    return detail


async def search_jsearch_jobs(
    query: str,
    location: Optional[str] = None,
    page: int = 1,
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "all",
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
        "country": country,
        "date_posted": date_posted,
    }

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
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

    payload = response.json()
    raw_jobs = payload.get("data", [])

    return [normalize_job_card(job) for job in raw_jobs]


async def get_jsearch_job_detail(
    job_id: str,
) -> JobDetailResponse:
    if not settings.JSEARCH_API_KEY:
        raise JSearchError("JSEARCH_API_KEY is missing in .env")

    url = settings.jsearch_detail_URL

    headers = {
        "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
        "X-RapidAPI-Host": settings.JSEARCH_API_HOST,
    }

    params = {
        "job_id": job_id,
    }

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise JSearchError(
            f"JSearch job detail API error {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        raise JSearchError(
            f"Could not connect to JSearch job detail API. "
            f"Error type: {type(e).__name__}. "
            f"Error: {repr(e)}"
        )

    payload = response.json()
    data = payload.get("data", [])

    if not data:
        raise JSearchError("No job detail found for this job_id")

    return normalize_job_detail(data[0])