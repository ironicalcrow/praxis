import re

from app.schemas import JobDetailResponse, JobRequirementProfile

class JobProfileExtractorError(Exception):
    pass

def unique_clean(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for item in items:
        if not item:
            continue

        clean = str(item).strip()

        if not clean:
            continue

        key = clean.lower()

        if key not in seen:
            seen.add(key)
            result.append(clean)

    return result


def normalize_technology_name(value: str) -> str:
    value = value.strip()

    aliases = {
        "Javascript": "JavaScript",
        "javascript": "JavaScript",
        "Typescript": "TypeScript",
        "typescript": "TypeScript",
        "NodeJS": "Node.js",
        "Nodejs": "Node.js",
        "nodejs": "Node.js",
        "Node": "Node.js",
        "REST APIs": "REST API development",
        "REST API": "REST API development",
        "REST": "REST API development",
        "Postgres": "PostgreSQL",
        "postgres": "PostgreSQL",
        "Mongo": "MongoDB",
        "mongo": "MongoDB",
    }

    return aliases.get(value, value)


def normalize_technology_list(items: list[str]) -> list[str]:
    normalized = []

    for item in items:
        if not item:
            continue

        normalized.append(normalize_technology_name(item))

    return unique_clean(normalized)


def build_summary(job: JobDetailResponse) -> str | None:
    parts = []

    if job.seniority_level:
        parts.append(job.seniority_level)

    if job.job_function:
        parts.append(job.job_function)

    if job.employment_type:
        parts.append(job.employment_type)

    if job.work_arrangement:
        parts.append(job.work_arrangement)

    role_text = " ".join(parts).strip()

    if role_text:
        return f"{job.title} is a {role_text} role."

    return job.title


def extract_education_requirements(job: JobDetailResponse) -> list[str]:
    text_sources = []

    text_sources.extend(job.highlights.qualifications)

    if job.description:
        text_sources.append(job.description)

    text = "\n".join(text_sources)

    patterns = [
        r"final year[^.\n]*",
        r"recent [^.\\n]*graduate[^.\\n]*",
        r"bachelor[^.\\n]*",
        r"bsc[^.\\n]*",
        r"computer science[^.\\n]*",
        r"software engineering[^.\\n]*",
    ]

    results = []

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        for match in matches:
            results.append(match.strip(" .•-\n"))

    return unique_clean(results)


def extract_important_context(job: JobDetailResponse) -> list[str]:
    if not job.description:
        return []

    description = job.description

    context_patterns = [
        r"\d+\s*hours?\s*per\s*week[^.\n]*",
        r"working hours[^.\n]*",
        r"between\s+\d+[^.\n]*",
        r"computer with good specifications[^.\n]*",
        r"stable internet connection[^.\n]*",
        r"resume and cover letter[^.\n]*",
        r"links to [^.\\n]*projects[^.\\n]*",
        r"references?[^.\\n]*",
        r"allowance[^.\\n]*",
        r"salary[^.\\n]*",
    ]

    results = []

    for pattern in context_patterns:
        matches = re.findall(pattern, description, flags=re.IGNORECASE)

        for match in matches:
            results.append(match.strip(" .•-\n"))

    return unique_clean(results)


async def extract_job_requirement_profile(
    job: JobDetailResponse,
) -> JobRequirementProfile:
    required_skills = normalize_technology_list(job.required_technologies)
    preferred_skills = normalize_technology_list(job.preferred_technologies)

    tools_and_technologies = unique_clean(
        required_skills
        + preferred_skills
        + normalize_technology_list(job.methodologies)
    )

    responsibilities = unique_clean(job.highlights.responsibilities)

    if not responsibilities and job.description:
        # Keep this conservative. Do not rewrite the company narrative.
        responsibility_markers = [
            "What you’ll do:",
            "What you'll do:",
            "Responsibilities:",
            "Key Responsibilities:",
        ]

        for marker in responsibility_markers:
            if marker.lower() in job.description.lower():
                responsibilities.append(marker.replace(":", " section found in description"))
                break

    qualifications = unique_clean(job.highlights.qualifications)

    benefits = unique_clean(
        job.highlights.benefits
        + job.benefits
        + job.benefits_extended
    )

    profile = JobRequirementProfile(
        summary=build_summary(job),
        description=job.description,

        required_skills=required_skills,
        preferred_skills=preferred_skills,

        tools_and_technologies=tools_and_technologies,
        methodologies=unique_clean(job.methodologies),
        soft_skills=unique_clean(job.soft_skills),

        responsibilities=responsibilities,
        qualifications=qualifications,
        benefits=benefits,

        required_experience_years=job.required_experience_years,
        seniority_level=job.seniority_level,

        job_function=job.job_function,
        industry=job.industry,
        work_arrangement=job.work_arrangement,

        education_requirements=extract_education_requirements(job),
        important_context=extract_important_context(job),
    )

    return profile