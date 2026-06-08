import uuid
import json
import re
import hashlib
import time
from typing import Any

from app.core.llm_caller import LLMCallerError, call_llm
from app.schemas import ResumeSchema
from app.core.session import get_session
from app.modules.jobs.models import JobQuery, SearchQuery


def fetch_job_queries_by_resume(resume_id: str) -> list[str]:
    db = get_session()
    try:
        rid = str(resume_id)
        queries = db.query(JobQuery).filter(JobQuery.resume_id == rid).order_by(JobQuery.priority).all()
        return [q.query for q in queries if q.query]
    finally:
        db.close()


def _get_or_create_search_query(db, query: str, location: str) -> str:
    raw_key = f"{query}_{location}".lower()
    hashed_id = hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    sq = db.query(SearchQuery).filter(SearchQuery.id == hashed_id).first()
    if not sq:
        sq = SearchQuery(
            id=hashed_id,
            query=query,
            location=location,
        )
        db.add(sq)
        db.flush()
    return hashed_id


async def get_or_generate_resume_job_queries(
    resume_id: str,
    resume: ResumeSchema,
    limit: int = 10,
    user_preferences: dict | None = None,
) -> list[str]:
    existing_queries = fetch_job_queries_by_resume(resume_id)
    if existing_queries:
        return existing_queries

    db = get_session()
    try:
        # Get location from resume
        loc = resume.location or resume.country or "Any"

        generated = await generate_resume_job_queries(
            resume=resume, user_preferences=user_preferences, limit=limit
        )

        saved_queries = []
        query_sq_pairs = []
        for item in generated:
            sq_id = _get_or_create_search_query(db, query=item["query"], location=loc)
            q = JobQuery(
                id=uuid.uuid4(),
                resume_id=str(resume_id),
                search_query_id=sq_id,
                query=item["query"],
                reason=item.get("reason"),
                priority=item.get("priority"),
            )
            db.add(q)
            saved_queries.append(item["query"])
            query_sq_pairs.append((item["query"], sq_id))
        db.commit()

        # Instantly enqueue to ARQ with search_query_id so jobs get linked
        try:
            from app.core.worker import redis_settings
            from arq import create_pool
            redis = await create_pool(redis_settings)
            for q_text, sq_id in query_sq_pairs:
                await redis.enqueue_job('collect_jobs_for_query', q_text, loc, sq_id)
            await redis.close()
        except Exception as e:
            print(f"[QueryService] Failed to enqueue background tasks: {e}")

        return saved_queries
    except Exception as e:
        db.rollback()
        return [item["query"] for item in generated] if 'generated' in locals() else []
    finally:
        db.close()


def delete_job_queries(resume_id: str) -> None:
    db = get_session()
    try:
        rid = str(resume_id)
        db.query(JobQuery).filter(JobQuery.resume_id == rid).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def refresh_resume_job_queries(
    resume_id: str,
    resume: ResumeSchema,
    limit: int = 10,
    user_preferences: dict | None = None,
) -> list[str]:
    db = get_session()
    try:
        rid = str(resume_id)
        # Preserve manual searches before wiping
        searched = db.query(JobQuery).filter(
            JobQuery.resume_id == rid,
            JobQuery.reason == "user searched"
        ).all()
        user_searched_texts = [q.query for q in searched]

        db.query(JobQuery).filter(JobQuery.resume_id == rid).delete()
        db.commit()
    finally:
        db.close()

    db = get_session()
    try:
        loc = resume.location or resume.country or "Any"

        generated = await generate_resume_job_queries(
            resume=resume,
            user_searched_queries=user_searched_texts,
            user_preferences=user_preferences,
            limit=limit,
        )

        rid = str(resume_id)
        saved_queries = []
        query_sq_pairs = []
        for item in generated:
            sq_id = _get_or_create_search_query(db, query=item["query"], location=loc)
            q = JobQuery(
                id=uuid.uuid4(),
                resume_id=rid,
                search_query_id=sq_id,
                query=item["query"],
                reason=item.get("reason", "resume based"),
                priority=item.get("priority", 5),
            )
            db.add(q)
            saved_queries.append(item["query"])
            query_sq_pairs.append((item["query"], sq_id))
        db.commit()

        # Instantly enqueue to ARQ with search_query_id so jobs get linked
        try:
            from app.core.worker import redis_settings
            from arq import create_pool
            redis = await create_pool(redis_settings)
            print(f"[QueryService] Enqueuing {len(saved_queries)} queries for location: {loc}")
            for q_text, sq_id in query_sq_pairs:
                print(f" -> collect_jobs_for_query: '{q_text}' in '{loc}'")
                await redis.enqueue_job('collect_jobs_for_query', q_text, loc, sq_id)
            await redis.close()
        except Exception as e:
            print(f"[QueryService] Failed to enqueue refreshed tasks: {e}")

        return saved_queries
    except Exception as e:
        db.rollback()
        print(f"[QueryService] Error during refresh: {e}")
        return [item["query"] for item in generated] if 'generated' in locals() else []
    finally:
        db.close()


class ResumeQueryGeneratorError(Exception):
    pass


DEFAULT_QUERY_LIMIT = 5


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
        result.append({
            "query": query,
            "reason": str(reason).strip() if reason else None,
            "priority": int(priority),
        })

        if len(result) >= limit:
            break

    return result


def build_resume_query_context(resume: ResumeSchema) -> dict[str, Any]:
    print(f"[QueryService] Compressing resume context for '{resume.name or 'unknown'}'...")
    return {
        "skills": resume.skills,
        "years_of_experience": resume.years_of_experience,
        "education_degrees": [item.degree for item in resume.education],
        "past_roles": [item.role for item in resume.experience],
        "certifications": resume.certifications,
        "location": resume.location or resume.country or "Any",
    }


def build_query_generation_prompt(
    resume: ResumeSchema,
    user_searched_queries: list[str] | None,
    user_preferences: dict | None,
    limit: int,
) -> str:
    context = build_resume_query_context(resume)

    if user_preferences:
        context["user_preferences"] = user_preferences

    past_searches_text = ""
    if user_searched_queries:
        past_searches_text = (
            f"\nUser's Recent Manual Searches (CRITICAL — strongly prioritize these):\n"
            f"{json.dumps(user_searched_queries)}\n"
        )

    return f"""
You generate a very small set of generalized job-search queries from a candidate resume.
{past_searches_text}
Goal:
Convert concrete skills, projects, certificates, and recent manual searches into broad job titles.

Rules:
- Return at most {limit} queries.
- Keep queries broad and searchable (e.g. "backend developer", "data analyst").
- If the user has Recent Manual Searches, ensure your queries strongly encompass what they are actively looking for.
- Pay close attention to User Preferences (job_types) when set.

Return ONLY valid JSON.

Required shape:
{{
  "queries": [
    {{
      "query": "backend developer",
      "priority": 1,
      "reason": "resume based"
    }}
  ]
}}

Resume context:
{json.dumps(context, ensure_ascii=False)}
""".strip()


async def generate_resume_job_queries(
    resume: ResumeSchema,
    user_searched_queries: list[str] | None = None,
    user_preferences: dict | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    # Fallback queries from resume skills if LLM fails
    def _skill_fallback() -> list[dict[str, Any]]:
        fallbacks = []
        for i, skill in enumerate(resume.skills[:limit]):
            fallbacks.append({"query": skill.lower(), "priority": i + 1, "reason": "fallback"})
        if not fallbacks and resume.experience:
            for i, exp in enumerate(resume.experience[:limit]):
                if exp.role:
                    fallbacks.append({"query": exp.role.lower(), "priority": i + 1, "reason": "fallback"})
        return fallbacks

    prompt = build_query_generation_prompt(
        resume=resume,
        user_searched_queries=user_searched_queries,
        user_preferences=user_preferences,
        limit=limit,
    )

    print(f"[QueryService] Hitting LLM to generate up to {limit} queries...")
    start_time = time.time()
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

        elapsed = time.time() - start_time
        print(f"[QueryService] LLM responded in {elapsed:.2f}s.")

        parsed = _extract_json(content)
        queries = normalize_generated_queries(_safe_list(parsed.get("queries")), limit=limit)

        if queries:
            print(f"[QueryService] Generated {len(queries)} valid queries.")
            return queries

    except (LLMCallerError, ResumeQueryGeneratorError, json.JSONDecodeError, ValueError) as e:
        print(f"[QueryService] LLM query generation failed: {e}. Using skill fallback.")

    fallback = _skill_fallback()
    if fallback:
        print(f"[QueryService] Returning {len(fallback)} fallback queries from resume skills.")
        return fallback

    raise ResumeQueryGeneratorError("Failed to generate queries and no skills available for fallback.")
