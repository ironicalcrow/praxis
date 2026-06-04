from app.schemas import ResumeSchema, JobCard
from app.modules.jobs.controller import get_job_detail, search_live_jobs
from app.modules.jobs.services.job_profile_extractor import extract_job_requirement_profile
from app.modules.jobs.services.suggestion_scorer import compute_batch_suggestion_scores


def get_job_unique_key(job: JobCard) -> str:
    if job.external_id:
        return f"id:{job.external_id}"

    if job.apply_url:
        return f"url:{job.apply_url}"

    return f"title-company:{job.title.lower()}:{(job.company or '').lower()}"


def cheap_skill_overlap_score(job: JobCard, resume: ResumeSchema) -> int:
    text = " ".join(
        [
            job.title or "",
            job.company or "",
            job.description_preview or "",
            job.location or "",
            job.employment_type or "",
        ]
    ).lower()

    score = 0

    for skill in resume.skills:
        if skill and skill.lower() in text:
            score += 1

    return score


async def build_job_pool_from_queries(
    queries: list[str] | None,
    candidate_resume: ResumeSchema,
    location: str | None = None,
    country: str = "bd",
    page: int = 1,
    num_pages: int = 1,
    max_jobs_per_query: int = 10,
    max_total_jobs: int = 30,
) -> list[dict]:
    resolved_queries = queries or []

    if not resolved_queries:
        resolved_queries = ["junior software engineer"]

    job_map: dict[str, JobCard] = {}

    for query in resolved_queries:
        jobs = await search_live_jobs(
            query=query,
            location=location,
            page=page,
            num_pages=num_pages,
            country=country,
            date_posted="all",
        )

        for job in jobs[:max_jobs_per_query]:
            unique_key = get_job_unique_key(job)

            if unique_key not in job_map:
                job_map[unique_key] = job

            if len(job_map) >= max_total_jobs:
                break

        if len(job_map) >= max_total_jobs:
            break

    candidate_jobs = list(job_map.values())

    # Cheap local pre-rank before expensive job detail/profile calls
    candidate_jobs.sort(
        key=lambda job: cheap_skill_overlap_score(job, candidate_resume),
        reverse=True,
    )

    candidate_jobs = candidate_jobs[:max_total_jobs]

    job_profiles = {}
    detailed_jobs_by_id = {}
    job_cards_by_id = {}

    for job_card in candidate_jobs:
        if not job_card.external_id:
            continue

        detail = await get_job_detail(job_card.external_id)

        if not detail:
            continue

        profile = await extract_job_requirement_profile(detail)

        job_profiles[job_card.external_id] = profile
        detailed_jobs_by_id[job_card.external_id] = detail
        job_cards_by_id[job_card.external_id] = job_card

    score_map = await compute_batch_suggestion_scores(
        candidate=candidate_resume,
        job_profiles=job_profiles,
    )

    ranked_jobs = []

    for job_id, detail in detailed_jobs_by_id.items():
        ranked_jobs.append(
            {
                "job": job_cards_by_id[job_id],
                "job_detail": detail,
                "suggestion_score": score_map.get(job_id, 0.0),
            }
        )

    ranked_jobs.sort(
        key=lambda item: item["suggestion_score"],
        reverse=True,
    )

    return ranked_jobs