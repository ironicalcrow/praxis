import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.modules.fit_score.schema import (
    CandidateFitProfile,
    FitScoreResponse,
)
from app.modules.jobs.schema import JobRequirementProfile


class FitScoreScorerError(Exception):
    pass


def clamp_fit_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    if score < 0:
        return 0.0

    if score > 100:
        return 100.0

    return round(score, 2)


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


def safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []

    for item in value:
        if item is None:
            continue

        text = str(item).strip()

        if text:
            result.append(text)

    return result


def build_job_context(profile: JobRequirementProfile) -> dict[str, Any]:
    return {
        "summary": profile.summary,
        "description": profile.description,
        "required_skills": profile.required_skills,
        "preferred_skills": profile.preferred_skills,
        "tools_and_technologies": profile.tools_and_technologies,
        "methodologies": profile.methodologies,
        "soft_skills": profile.soft_skills,
        "responsibilities": profile.responsibilities,
        "qualifications": profile.qualifications,
        "benefits": profile.benefits,
        "required_experience_years": profile.required_experience_years,
        "seniority_level": profile.seniority_level,
        "job_function": profile.job_function,
        "industry": profile.industry,
        "work_arrangement": profile.work_arrangement,
        "education_requirements": profile.education_requirements,
        "important_context": profile.important_context,
    }


def build_candidate_context(candidate: CandidateFitProfile) -> dict[str, Any]:
    return {
        "summary": candidate.summary,
        "skills": candidate.skills,
        "tools_and_technologies": candidate.tools_and_technologies,
        "methodologies": candidate.methodologies,
        "soft_skills": candidate.soft_skills,
        "projects": [
            {
                "title": project.title,
                "description": project.description,
                "technologies": project.technologies,
            }
            for project in candidate.projects
        ],
        "years_experience": candidate.years_experience,
        "preferred_roles": candidate.preferred_roles,
        "preferred_work_arrangement": candidate.preferred_work_arrangement,
        "education": candidate.education,
    }


def build_fit_score_prompt(
    profile: JobRequirementProfile,
    candidate: CandidateFitProfile,
) -> str:
    job_context = build_job_context(profile)
    candidate_context = build_candidate_context(candidate)

    return f"""
You are a strict but fair job-candidate fit evaluator.

Your task:
Evaluate how well the candidate fits the job.

Return a final fit score from 0 to 100.

Important rules:
- Do NOT invent candidate experience.
- Do NOT invent job requirements.
- Use only the provided job context and candidate context.
- Be strict but fair.
- If a requirement is missing or unclear in the candidate profile, treat it as a weakness.
- If a candidate project uses the required technology or a very similar technology, count it as strong evidence.
- If a candidate project has similar responsibilities but different technologies, give partial credit.
- If the candidate has a similar academic or professional background, count it positively.
- For developer/software roles, CS, CSE, Software Engineering, backend/frontend/full-stack projects are relevant.
- For marketing/business/design roles, relevant education, projects, domain, and responsibilities should matter.
- Consider whether the candidate background is close to the job function, industry, and responsibilities.
- Consider required skills, preferred skills, tools, technologies, methods, soft skills, responsibilities, education, experience, seniority, and work arrangement.
- Do not over-score just because one or two keywords match.
- Do not under-score if different words describe the same practical capability.

Fit score guide:
- 90-100: Almost perfect match. Most core requirements and project/experience evidence are present.
- 75-89: Strong fit. Core requirements mostly match, with some minor gaps.
- 60-74: Moderate fit. Some strong matches, but noticeable gaps.
- 40-59: Weak fit. Limited match, several important gaps.
- 0-39: Poor fit. Little evidence of fit.

Return ONLY valid JSON.
Do not wrap JSON in markdown.
Do not add explanation outside JSON.

Required JSON shape:
{{
  "fit_score": number,
  "strengths": string[],
  "weaknesses": string[],
  "reason": string
}}

What to include:
- strengths: concrete reasons why the candidate matches.
- weaknesses: concrete gaps or unclear areas.
- reason: one concise paragraph explaining the final score.

Job context:
{json.dumps(job_context, ensure_ascii=False)}

Candidate context:
{json.dumps(candidate_context, ensure_ascii=False)}
""".strip()


def extract_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1:
            raise FitScoreScorerError("LLM did not return valid JSON")

        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as e:
            raise FitScoreScorerError(
                f"Could not parse JSON from LLM output: {e}"
            )


async def call_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"

    model = getattr(
        settings,
        "OLLAMA_FIT_SCORER_MODEL",
        getattr(settings, "OLLAMA_JOB_PROFILE_MODEL", "qwen2.5:3b"),
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You evaluate job-candidate fit. "
                    "Return only valid JSON with fit_score, strengths, weaknesses, and reason."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,
        },
    }

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    data = response.json()
    return data.get("message", {}).get("content", "")


async def call_groq(prompt: str) -> str:
    if not settings.GROQ_API_KEY:
        raise FitScoreScorerError("GROQ_API_KEY is missing")

    url = "https://api.groq.com/openai/v1/chat/completions"

    model = getattr(
        settings,
        "GROQ_FIT_SCORER_MODEL",
        getattr(settings, "GROQ_JOB_PROFILE_MODEL", "llama-3.1-8b-instant"),
    )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You evaluate job-candidate fit. "
                    "Return only valid JSON with fit_score, strengths, weaknesses, and reason."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


async def call_fit_scorer_llm(prompt: str) -> str:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return await call_ollama(prompt)

    if provider == "groq":
        return await call_groq(prompt)

    raise FitScoreScorerError(f"Unsupported LLM_PROVIDER: {provider}")


def build_fit_score_response(parsed: dict[str, Any]) -> FitScoreResponse:
    score = clamp_fit_score(parsed.get("fit_score"))
    verdict = get_verdict(score)

    strengths = safe_string_list(parsed.get("strengths"))
    weaknesses = safe_string_list(parsed.get("weaknesses"))

    reason = parsed.get("reason")

    if not reason:
        reason = "The fit score was generated based on the provided job requirements and candidate profile."

    return FitScoreResponse(
        fit_score=score,
        verdict=verdict,
        strengths=strengths,
        weaknesses=weaknesses,
        reason=str(reason).strip(),
    )


async def compute_fit_score(
    profile: JobRequirementProfile,
    candidate: CandidateFitProfile,
) -> FitScoreResponse:
    prompt = build_fit_score_prompt(
        profile=profile,
        candidate=candidate,
    )

    content = await call_fit_scorer_llm(prompt)

    if not content:
        raise FitScoreScorerError("LLM returned empty fit score response")

    parsed = extract_json_from_text(content)

    try:
        return build_fit_score_response(parsed)

    except ValidationError as e:
        raise FitScoreScorerError(
            f"Invalid FitScoreResponse schema: {str(e)}"
        )