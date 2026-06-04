import uuid
import json
import re
from typing import Any

from app.core.llm_caller import LLMCallerError, call_llm
from app.schemas import ResumeSchema
from app.core.session import get_session
from app.modules.jobs.models import JobQuery


def fetch_job_queries_by_resume(resume_id: str) -> list[str]:
    db = get_session()
    try:
        rid = uuid.UUID(resume_id) if isinstance(resume_id, str) else resume_id
        queries = db.query(JobQuery).filter(JobQuery.resume_id == rid).order_by(JobQuery.priority).all()
        return [q.query for q in queries if q.query]
    finally:
        db.close()


async def get_or_generate_resume_job_queries(
    resume_id: str,
    resume: ResumeSchema,
    limit: int = 5,
) -> list[str]:
    existing_queries = fetch_job_queries_by_resume(resume_id)
    if existing_queries:
        return existing_queries

    generated = await generate_resume_job_queries(resume=resume, limit=limit)
    
    db = get_session()
    try:
        saved_queries = []
        for item in generated:
            q = JobQuery(
                id=uuid.uuid4(),
                resume_id=uuid.UUID(resume_id) if isinstance(resume_id, str) else resume_id,
                query=item["query"],
                reason=item.get("reason"),
                priority=item.get("priority"),
            )
            db.add(q)
            saved_queries.append(item["query"])
        db.commit()
        return saved_queries
    except Exception:
        db.rollback()
        return [item["query"] for item in generated]
    finally:
        db.close()



class ResumeQueryGeneratorError(Exception):
    pass


DEFAULT_QUERY_LIMIT = 5


BACKEND_SKILLS = {
    "fastapi", "django", "flask", "express", "node", "node.js", "nestjs",
    "spring", "spring boot", "laravel", "postgres", "postgresql", "mysql",
    "mongodb", "redis", "sqlalchemy", "rest", "api", "graphql",
}

FRONTEND_SKILLS = {
    "react", "next", "next.js", "vue", "angular", "javascript", "typescript",
    "html", "css", "tailwind", "bootstrap", "frontend",
}

AI_ML_SKILLS = {
    "machine learning", "ml", "ai", "artificial intelligence", "deep learning",
    "pytorch", "tensorflow", "scikit", "scikit-learn", "computer vision",
    "nlp", "transformer", "llm", "yolo", "opencv", "pandas", "numpy",
}

DEVOPS_SKILLS = {
    "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "linux",
}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ResumeQueryGeneratorError("LLM did not return valid JSON")

        return json.loads(match.group(0))


def _clean_query(value: Any) -> str | None:
    if value is None:
        return None

    query = str(value).strip().lower()
    query = re.sub(r"\s+", " ", query)

    if not query or len(query) > 80:
        return None

    # Avoid technology soup like "fastapi/react/js"
    if "," in query or "/" in query:
        return None

    return query


def normalize_generated_queries(
    raw_items: list[Any],
    limit: int = DEFAULT_QUERY_LIMIT,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []

    for index, item in enumerate(raw_items):
        if isinstance(item, str):
            query = _clean_query(item)
            reason = None
            priority = index + 1

        elif isinstance(item, dict):
            query = _clean_query(item.get("query"))
            reason = item.get("reason")
            priority = item.get("priority") or index + 1

        else:
            continue

        if not query or query in seen:
            continue

        seen.add(query)

        result.append(
            {
                "query": query,
                "reason": str(reason).strip() if reason else None,
                "priority": int(priority),
            }
        )

        if len(result) >= limit:
            break

    return result


def build_resume_query_context(resume: ResumeSchema) -> dict[str, Any]:
    return {
        "skills": resume.skills,
        "years_of_experience": resume.years_of_experience,
        "education": [
            {
                "degree": item.degree,
                "institution": item.institution,
            }
            for item in resume.education
        ],
        "experience": [
            {
                "role": item.role,
                "description": item.description,
            }
            for item in resume.experience
        ],
        "projects": [
            {
                "name": project.name,
                "description": project.description,
                "technology": project.technology,
            }
            for project in resume.projects
        ],
        "certifications": resume.certifications,
    }


def build_query_generation_prompt(resume: ResumeSchema, limit: int) -> str:
    context = build_resume_query_context(resume)

    return f"""
You generate a very small set of generalized job-search queries from a candidate resume.

Goal:
Convert concrete skills, projects, and certificates into broad job titles.

Examples:
- FastAPI + React + JavaScript + database/API projects => backend developer, full stack developer
- React + JavaScript + UI projects => frontend developer
- ML/AI/deep learning/computer vision/NLP projects or certificates => ml engineer, ai engineer, machine learning intern
- Docker/cloud/CI/CD/Linux deployment work => devops engineer

Rules:
- Return at most {limit} queries.
- Keep queries broad and searchable.
- Do not output long keyword strings.
- Do not include duplicate meanings.
- Prefer intern/junior queries when experience is low or the resume is student-like.
- If both backend and frontend evidence exist, include full stack developer.
- If AI/ML evidence exists, include at least one AI/ML query.
- Return ONLY valid JSON.

Required JSON shape:
{{
  "queries": [
    {{"query": "backend developer", "priority": 1, "reason": "FastAPI/API/database evidence"}}
  ]
}}

Resume context:
{json.dumps(context, ensure_ascii=False)}
""".strip()


def generate_fallback_queries(
    resume: ResumeSchema,
    limit: int = DEFAULT_QUERY_LIMIT,
) -> list[dict[str, Any]]:
    evidence = " ".join(
        [
            " ".join(resume.skills or []),
            " ".join(resume.certifications or []),
            " ".join(
                " ".join(
                    [
                        project.name or "",
                        project.description or "",
                        project.technology or "",
                    ]
                )
                for project in resume.projects
            ),
            " ".join(
                " ".join([exp.role or "", exp.description or ""])
                for exp in resume.experience
            ),
        ]
    ).lower()

    selected: list[tuple[str, str]] = []

    has_backend = any(skill in evidence for skill in BACKEND_SKILLS)
    has_frontend = any(skill in evidence for skill in FRONTEND_SKILLS)
    has_ai_ml = any(skill in evidence for skill in AI_ML_SKILLS)
    has_devops = any(skill in evidence for skill in DEVOPS_SKILLS)

    if has_backend and has_frontend:
        selected.append(("full stack developer", "Both backend and frontend evidence found"))

    if has_backend:
        selected.append(("backend developer", "Backend/API/database evidence found"))

    if has_frontend:
        selected.append(("frontend developer", "Frontend/UI evidence found"))

    if has_ai_ml:
        selected.append(("ml engineer", "AI/ML evidence found"))
        selected.append(("machine learning intern", "AI/ML evidence with student/intern-friendly role"))

    if has_devops:
        selected.append(("devops engineer", "DevOps/deployment evidence found"))

    if not selected:
        selected.append(("junior software engineer", "General software profile"))

    result = []
    seen = set()

    for query, reason in selected:
        if query in seen:
            continue

        seen.add(query)

        result.append(
            {
                "query": query,
                "reason": reason,
                "priority": len(result) + 1,
            }
        )

        if len(result) >= limit:
            break

    return result


async def generate_resume_job_queries(
    resume: ResumeSchema,
    limit: int = DEFAULT_QUERY_LIMIT,
) -> list[dict[str, Any]]:
    prompt = build_query_generation_prompt(resume=resume, limit=limit)

    try:
        content = await call_llm(
            temperature=0.0,
            json_mode=True,
            messages=[
                {
                    "role": "system",
                    "content": "You convert resumes into minimal generalized job-search queries. Return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        parsed = _extract_json(content)
        queries = normalize_generated_queries(
            _safe_list(parsed.get("queries")),
            limit=limit,
        )

        if queries:
            return queries

    except (LLMCallerError, ResumeQueryGeneratorError, json.JSONDecodeError, ValueError):
        pass

    return generate_fallback_queries(resume=resume, limit=limit)