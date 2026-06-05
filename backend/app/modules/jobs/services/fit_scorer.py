import json
from typing import Any

from pydantic import ValidationError

from app.core.llm_caller import LLMCallerError, call_llm
from app.schemas import(
    ResumeSchema,
    FitScoreResponse,
    JobRequirementProfile
)

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
        "required_experience_years": profile.required_experience_years,
        "seniority_level": profile.seniority_level,
        "job_function": profile.job_function,
        "industry": profile.industry,
        "work_arrangement": profile.work_arrangement,
        "education_requirements": profile.education_requirements,
        "important_context": profile.important_context,
    }


def build_candidate_context(candidate: ResumeSchema) -> dict[str, Any]:
    return {
        "name": candidate.name,
        "location": candidate.location,
        "skills": candidate.skills,
        "experience": [
            {
                "role": item.role,
                "organization": item.organization,
                "description": item.description,
            }
            for item in candidate.experience
        ],
        "projects": [
            {
                "name": project.name,
                "description": project.description,
                "technology": project.technology,
            }
            for project in candidate.projects
        ],
        "education": [
            {
                "degree": item.degree,
                "institution": item.institution,
                "year": item.year,
                "gpa": item.gpa,
            }
            for item in candidate.education
        ],
        "certifications": candidate.certifications,
        "years_of_experience": candidate.years_of_experience,
        "raw_text": candidate.raw_text,
    }


def build_fit_score_prompt(
    profile: JobRequirementProfile,
    candidate: ResumeSchema,
    add_reasoning: bool = True,
) -> str:
    job_context = build_job_context(profile)
    candidate_context = build_candidate_context(candidate)

    if add_reasoning:
        required_json_shape = """
{
  "fit_score": number,
  "strengths": string[],
  "weaknesses": string[],
  "reason": string
}
""".strip()
    else:
        required_json_shape = """
{
  "fit_score": number
}
""".strip()

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
- Consider required skills, preferred skills, tools, technologies, responsibilities, education, experience, seniority, and work arrangement.
- Do not over-score just because one or two keywords match.
- Do not under-score if different words describe the same practical capability.

Fit score guide:
- 90-100: Almost perfect match.
- 75-89: Strong fit.
- 60-74: Moderate fit.
- 40-59: Weak fit.
- 0-39: Poor fit.

Return ONLY valid JSON.
Do not wrap JSON in markdown.
Do not add explanation outside JSON.

Required JSON shape:
{required_json_shape}

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


async def call_fit_scorer_llm(
    prompt: str,
    add_reasoning: bool = True,
) -> str:
    if add_reasoning:
        system_content = (
            "You evaluate job-candidate fit. "
            "Return only valid JSON with fit_score, strengths, weaknesses, and reason."
        )
    else:
        system_content = (
            "You evaluate job-candidate fit. "
            "Return only valid JSON with fit_score."
        )

    try:
        return await call_llm(
            temperature=0.0,
            json_mode=True,
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    except LLMCallerError as e:
        raise FitScoreScorerError(str(e))


def build_fit_score_response(
    parsed: dict[str, Any],
    add_reasoning: bool = True,
) -> FitScoreResponse:
    score = clamp_fit_score(parsed.get("fit_score"))
    verdict = get_verdict(score)

    if not add_reasoning:
        return FitScoreResponse(
            fit_score=score,
            verdict=verdict,
            strengths=[],
            weaknesses=[],
            reason="Reasoning disabled for job suggestion ranking.",
        )

    strengths = safe_string_list(parsed.get("strengths"))
    weaknesses = safe_string_list(parsed.get("weaknesses"))

    reason = parsed.get("reason")

    if not reason:
        reason = "The fit score was generated based on the provided job requirements and candidate resume."

    return FitScoreResponse(
        fit_score=score,
        verdict=verdict,
        strengths=strengths,
        weaknesses=weaknesses,
        reason=str(reason).strip(),
    )


async def compute_fit_score(
    profile: JobRequirementProfile,
    candidate: ResumeSchema,
    add_reasoning: bool = True,
) -> FitScoreResponse:
    prompt = build_fit_score_prompt(
        profile=profile,
        candidate=candidate,
        add_reasoning=add_reasoning,
    )

    content = await call_fit_scorer_llm(
        prompt=prompt,
        add_reasoning=add_reasoning,
    )

    parsed = extract_json_from_text(content)

    try:
        return build_fit_score_response(
            parsed=parsed,
            add_reasoning=add_reasoning,
        )

    except ValidationError as e:
        raise FitScoreScorerError(
            f"Invalid FitScoreResponse schema: {str(e)}"
        )