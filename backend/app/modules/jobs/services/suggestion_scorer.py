import json
import re
from typing import Any

from app.core.llm_caller import LLMCallerError, call_llm
from app.schemas import JobRequirementProfile, ResumeSchema


class SuggestionScorerError(Exception):
    pass


def clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    return round(max(0.0, min(100.0, score)), 2)


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)

        if not match:
            raise SuggestionScorerError("LLM did not return valid JSON")

        return json.loads(match.group(0))


def build_light_resume_context(candidate: ResumeSchema) -> dict[str, Any]:
    return {
        "skills": candidate.skills,
        "years_of_experience": candidate.years_of_experience,
        "education": [
            {
                "degree": item.degree,
                "institution": item.institution,
            }
            for item in candidate.education
        ],
        "projects": [
            {
                "name": project.name,
                "description": project.description,
                "technology": project.technology,
            }
            for project in candidate.projects
        ],
        "certifications": candidate.certifications,
    }


def build_light_job_context(
    job_id: str,
    profile: JobRequirementProfile,
) -> dict[str, Any]:
    keywords = []

    keywords.extend(profile.required_skills or [])
    keywords.extend(profile.preferred_skills or [])
    keywords.extend(profile.tools_and_technologies or [])
    keywords.extend(profile.methodologies or [])
    keywords.extend(profile.soft_skills or [])
    keywords.extend(profile.qualifications or [])
    keywords.extend(profile.responsibilities or [])

    cleaned_keywords = []
    seen = set()

    for item in keywords:
        if not item:
            continue

        text = str(item).strip()
        key = text.lower()

        if key in seen:
            continue

        seen.add(key)
        cleaned_keywords.append(text)

    return {
        "job_id": job_id,
        "summary": profile.summary,
        "job_function": profile.job_function,
        "seniority_level": profile.seniority_level,
        "required_experience_years": profile.required_experience_years,
        "work_arrangement": profile.work_arrangement,
        "keywords": cleaned_keywords[:45],
    }


def build_batch_suggestion_prompt(
    candidate: ResumeSchema,
    job_contexts: list[dict[str, Any]],
) -> str:
    return f"""
You are ranking jobs for a recommendation feed, not doing a deep fit-score explanation.

Task:
For each job, return a lightweight suggestion_score from 0 to 100.

Use:
- Candidate skills, projects, certificates, education, and experience years.
- Job required skills, preferred skills, tools, soft skills, responsibilities, qualifications, seniority, and role function.

Rules:
- Score higher when the job role and required keywords align with the candidate.
- Score lower for senior roles if the candidate has low experience.
- Do not invent missing candidate skills.
- This is only for ranking a suggestion list, so do not return strengths, weaknesses, or long reasoning.
- Return every provided job_id exactly once.
- Return ONLY valid JSON.

Required JSON shape:
{{
  "scores": [
    {{"job_id": "abc", "suggestion_score": 82}}
  ]
}}

Candidate:
{json.dumps(build_light_resume_context(candidate), ensure_ascii=False)}

Jobs:
{json.dumps(job_contexts, ensure_ascii=False)}
""".strip()


def parse_score_map(parsed: dict[str, Any]) -> dict[str, float]:
    score_map: dict[str, float] = {}
    raw_scores = parsed.get("scores")

    if not isinstance(raw_scores, list):
        return score_map

    for item in raw_scores:
        if not isinstance(item, dict):
            continue

        job_id = str(item.get("job_id") or "").strip()

        if not job_id:
            continue

        score_map[job_id] = clamp_score(item.get("suggestion_score"))

    return score_map


def fallback_keyword_score(
    candidate: ResumeSchema,
    profile: JobRequirementProfile,
) -> float:
    candidate_text = " ".join(
        [
            " ".join(candidate.skills or []),
            " ".join(candidate.certifications or []),
            " ".join(
                " ".join(
                    [
                        project.name or "",
                        project.description or "",
                        project.technology or "",
                    ]
                )
                for project in candidate.projects
            ),
        ]
    ).lower()

    job_keywords = []
    job_keywords.extend(profile.required_skills or [])
    job_keywords.extend(profile.preferred_skills or [])
    job_keywords.extend(profile.tools_and_technologies or [])
    job_keywords.extend(profile.methodologies or [])
    job_keywords.extend(profile.soft_skills or [])

    unique_keywords = []
    seen = set()

    for keyword in job_keywords:
        key = str(keyword).strip().lower()

        if key and key not in seen:
            seen.add(key)
            unique_keywords.append(key)

    if not unique_keywords:
        return 40.0

    matches = sum(1 for keyword in unique_keywords if keyword in candidate_text)

    base_score = 35 + (matches / max(len(unique_keywords), 1)) * 60

    if profile.required_experience_years and candidate.years_of_experience is not None:
        if candidate.years_of_experience + 1 < profile.required_experience_years:
            base_score -= 15

    return clamp_score(base_score)


async def compute_batch_suggestion_scores(
    *,
    candidate: ResumeSchema,
    job_profiles: dict[str, JobRequirementProfile],
) -> dict[str, float]:
    if not job_profiles:
        return {}

    job_contexts = [
        build_light_job_context(job_id=job_id, profile=profile)
        for job_id, profile in job_profiles.items()
    ]

    prompt = build_batch_suggestion_prompt(
        candidate=candidate,
        job_contexts=job_contexts,
    )

    try:
        content = await call_llm(
            temperature=0.0,
            json_mode=True,
            messages=[
                {
                    "role": "system",
                    "content": "You rank job suggestions. Return only valid JSON with job_id to suggestion_score.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        parsed = extract_json(content)
        score_map = parse_score_map(parsed)

    except (LLMCallerError, SuggestionScorerError, json.JSONDecodeError, ValueError):
        score_map = {}

    # Fallback per missing job
    for job_id, profile in job_profiles.items():
        if job_id not in score_map:
            score_map[job_id] = fallback_keyword_score(candidate, profile)

    return score_map