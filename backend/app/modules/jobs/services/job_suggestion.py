"""
Suggestion pool with cursor-based windowing.

Pool (Redis): 50 pre-ranked jobs per user, ordered by blended fit score.
Window: 10 jobs shown at a time.
Prefetch threshold (60%): fire-and-forget ARQ scrape.
Regen threshold (100%): cycle pool from start + trigger background LLM query regen.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from app.schemas import ResumeSchema, JobSchema, JobRequirementProfile
from app.core.session import SessionLocal
from app.modules.jobs.models import Job, UserPreference
from app.core.llm_caller import embed_text
from app.modules.jobs.services.fit_scorer import compute_fit_score

# --- Pool constants ---
POOL_SIZE = 50
WINDOW_SIZE = 10
PREFETCH_THRESHOLD = 0.6   # trigger background scrape at 60% consumed
POOL_TTL_SECONDS = 86400   # 24h
RECENCY_DAYS = 30          # only show jobs posted within last 30 days (or NULL)


def _pool_key(user_id: str) -> str:
    return f"suggestion_pool:{user_id}"


def _offset_key(user_id: str) -> str:
    return f"suggestion_offset:{user_id}"


def _job_to_profile(job) -> JobRequirementProfile:
    skills = list(job.skills_and_technologies or []) if hasattr(job, 'skills_and_technologies') else []
    return JobRequirementProfile(
        summary=getattr(job, 'description', None) or "",
        description=getattr(job, 'description', None) or "",
        required_skills=skills,
        preferred_skills=[],
        tools_and_technologies=skills,
        soft_skills=[],
        qualifications=list(job.qualifications or []) if hasattr(job, 'qualifications') else [],
        responsibilities=list(job.responsibilities or []) if hasattr(job, 'responsibilities') else [],
    )


async def _get_redis():
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL)


async def build_suggestion_pool(
    user_id: str,
    candidate_resume: ResumeSchema,
    queries: list[str],
) -> dict:
    """
    Build or rebuild the suggestion pool for a user:
    1. Fetch resume + preference embeddings from DB.
    2. pgvector cosine search (with recency filter), capturing distances.
    3. Fallback: live JSearch if DB is empty.
    4. Compute blended fit scores (skill overlap + semantic similarity).
    5. Store pool in Redis, reset offset.
    6. Return first window.
    """
    r = await _get_redis()

    # --- 1. Fetch vectors ---
    def fetch_data():
        from app.modules.CV.models import Resume
        with SessionLocal() as db:
            pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
            resume = db.query(Resume).filter(Resume.user_id == str(user_id)).first()
            return (
                pref,
                list(resume.embedding) if resume and resume.embedding is not None else None,
                str(resume.id) if resume else None,
                list(pref.preference_embedding) if pref and pref.preference_embedding is not None else None,
            )

    prefs, resume_vec, fetched_resume_id, pref_vec = await asyncio.to_thread(fetch_data)

    user_vector: Optional[list] = None
    if resume_vec and pref_vec:
        user_vector = (np.array(resume_vec) * 0.7 + np.array(pref_vec) * 0.3).tolist()
        print("[JobSuggestion] 🔀 Using combined resume+preference vector (70/30).")
    elif resume_vec:
        user_vector = resume_vec
        print("[JobSuggestion] 🚀 Using pre-calculated CV vector.")
    else:
        # No stored vector — generate on the fly from resume text
        print("[JobSuggestion] ⚠️ No pre-calculated vector. Generating from resume text...")
        parts = []
        if candidate_resume.location:
            parts.append(f"Location: {candidate_resume.location}.")
        parts.append("Skills: " + ", ".join(candidate_resume.skills) + ".")
        if candidate_resume.raw_text:
            parts.append(candidate_resume.raw_text[:500])
        for exp in candidate_resume.experience:
            parts.append(f"{exp.role} at {exp.organization}.")
        resume_text = " ".join(parts)
        try:
            user_vector = await embed_text(resume_text)
            if fetched_resume_id:
                from app.modules.CV.db_service import update_resume_embedding
                await asyncio.to_thread(update_resume_embedding, fetched_resume_id, user_vector)
                print("[JobSuggestion] 💾 Saved generated CV vector to DB.")
        except Exception as e:
            print(f"[JobSuggestion] ⚠️ Embedding generation failed: {e}. Will use recency fallback.")

    # --- 2. pgvector search with recency filter ---
    rows: list[tuple[Job, Optional[float]]] = []

    if user_vector:
        def fetch_semantic_jobs():
            thirty_days_ago = datetime.utcnow() - timedelta(days=RECENCY_DAYS)
            with SessionLocal() as db:
                try:
                    dist_col = Job.embedding.cosine_distance(user_vector).label('dist')
                    return (
                        db.query(Job, dist_col)
                        .filter(Job.embedding.is_not(None))
                        .filter(
                            (Job.posted_at >= thirty_days_ago) | (Job.posted_at.is_(None))
                        )
                        .order_by(dist_col)
                        .limit(POOL_SIZE)
                        .all()
                    )
                except Exception as e:
                    print(f"[JobSuggestion] ⚠️ pgvector search failed: {e}. Falling back to recency sort.")
                    # Recency fallback — no semantic scoring
                    jobs = (
                        db.query(Job)
                        .filter(
                            (Job.posted_at >= thirty_days_ago) | (Job.posted_at.is_(None))
                        )
                        .order_by(Job.posted_at.desc().nullslast())
                        .limit(POOL_SIZE)
                        .all()
                    )
                    return [(j, None) for j in jobs]

        t0 = time.time()
        rows = await asyncio.to_thread(fetch_semantic_jobs)
        print(f"[JobSuggestion] pgvector search returned {len(rows)} jobs in {time.time()-t0:.2f}s.")
    else:
        # No vector at all — recency fallback
        def fetch_recency_jobs():
            thirty_days_ago = datetime.utcnow() - timedelta(days=RECENCY_DAYS)
            with SessionLocal() as db:
                jobs = (
                    db.query(Job)
                    .filter(
                        (Job.posted_at >= thirty_days_ago) | (Job.posted_at.is_(None))
                    )
                    .order_by(Job.posted_at.desc().nullslast())
                    .limit(POOL_SIZE)
                    .all()
                )
                return [(j, None) for j in jobs]

        rows = await asyncio.to_thread(fetch_recency_jobs)
        print(f"[JobSuggestion] Recency fallback returned {len(rows)} jobs.")

    # --- 3. Empty DB fallback — live JSearch seed ---
    if not rows and queries:
        print("[JobSuggestion] DB empty — seeding pool from live JSearch for top query...")
        try:
            from app.providers import JSearchScraper
            from app.modules.jobs.services.jsearch_parser import parse_jsearch_to_schema
            scraper = JSearchScraper()
            live_jobs = await scraper.search_jobs(
                queries[0],
                location=candidate_resume.location or "",
                limit=10,
            )
            pool_data = []
            for rj in live_jobs:
                try:
                    parsed = parse_jsearch_to_schema(rj)
                    schema = JobSchema(
                        id=parsed.external_id,
                        external_id=parsed.external_id,
                        provider_id=parsed.provider_id,
                        title=parsed.title,
                        company_name=parsed.company_name,
                        location=parsed.location,
                        apply_urls=parsed.apply_urls or [],
                        description=parsed.description,
                        posted_at=parsed.posted_at,
                        skills_and_technologies=parsed.skills_and_technologies or [],
                        responsibilities=parsed.responsibilities or [],
                        job_types=parsed.job_types or [],
                    )
                    pool_data.append(schema.model_dump(mode='json'))
                except Exception:
                    pass
            print(f"[JobSuggestion] Live seed produced {len(pool_data)} jobs.")
        except Exception as e:
            print(f"[JobSuggestion] Live seed failed: {e}. Returning empty pool.")
            pool_data = []

        # Store live seed in Redis
        try:
            await r.setex(_pool_key(user_id), POOL_TTL_SECONDS, json.dumps(pool_data))
            await r.set(_offset_key(user_id), 0)
        except Exception:
            pass
        await r.aclose()
        return _make_window(pool_data, 0)

    # --- 4. Compute blended fit scores ---
    print(f"[JobSuggestion] Computing fit scores for {len(rows)} jobs...")
    t1 = time.time()
    pool_data = []
    for db_job, cosine_dist in rows:
        semantic_sim = max(0.0, 1.0 - float(cosine_dist)) if cosine_dist is not None else None
        schema = JobSchema(
            id=db_job.id,
            external_id=db_job.external_id,
            provider_id=db_job.provider_id,
            title=db_job.title,
            company_name=db_job.company_name,
            location=db_job.location,
            posted_at=db_job.posted_at,
            apply_urls=db_job.apply_urls or [],
            description=db_job.description,

            skills_and_technologies=db_job.skills_and_technologies or [],
            responsibilities=db_job.responsibilities or [],
            job_types=db_job.job_types or [],
            metadata=db_job.job_metadata or {},
        )
        try:
            profile = _job_to_profile(db_job)
            schema.fit_score = await compute_fit_score(
                profile=profile,
                candidate=candidate_resume,
                semantic_similarity=semantic_sim,
            )
        except Exception as e:
            print(f"[JobSuggestion] Fit score failed for {db_job.id}: {e}")

        pool_data.append(schema.model_dump(mode='json'))

    print(f"[JobSuggestion] Fit scores computed in {time.time()-t1:.2f}s.")

    # --- 5. Store pool + reset offset ---
    try:
        await r.setex(_pool_key(user_id), POOL_TTL_SECONDS, json.dumps(pool_data))
        await r.set(_offset_key(user_id), 0)
        print(f"[JobSuggestion] ✅ Pool of {len(pool_data)} jobs stored in Redis.")
        from app.modules.notifications.service import create_and_publish as notify
        asyncio.create_task(notify(
            user_id=user_id,
            type="job_suggestions_ready",
            title="Job suggestions ready",
            message=f"We found {len(pool_data)} job matches based on your CV. Check them out!",
            data={"pool_total": len(pool_data)},
        ))
    except Exception as e:
        print(f"[JobSuggestion] ⚠️ Failed to cache pool in Redis: {e}")

    await r.aclose()
    return _make_window(pool_data, 0)


def _make_window(pool: list, offset: int) -> dict:
    window = pool[offset: offset + WINDOW_SIZE]
    return {
        "jobs": window,
        "jobs_seen": min(offset + WINDOW_SIZE, len(pool)),
        "pool_total": len(pool),
        "prefetch_triggered": False,
        "pool_cycling": False,
    }


async def get_suggestion_window(user_id: str) -> Optional[dict]:
    """
    Return the current window without advancing the cursor.
    Returns None if no pool exists (caller must build it).
    """
    r = await _get_redis()
    try:
        pool_raw = await r.get(_pool_key(user_id))
        offset = int(await r.get(_offset_key(user_id)) or 0)
    except Exception:
        pool_raw = None
        offset = 0
    finally:
        await r.aclose()

    if not pool_raw:
        return None

    pool = json.loads(pool_raw)
    return _make_window(pool, offset)


async def advance_suggestion_window(
    user_id: str,
    queries: list[str],
    candidate_resume: ResumeSchema,
    resume_id: str,
) -> dict:
    """
    Advance the cursor by one window and return the next batch of jobs.
    Triggers prefetch at 60% consumed. Cycles pool at 100% and regenerates queries in background.
    """
    r = await _get_redis()
    try:
        pool_raw = await r.get(_pool_key(user_id))
        offset = int(await r.get(_offset_key(user_id)) or 0)
    except Exception:
        pool_raw = None
        offset = 0

    if not pool_raw:
        await r.aclose()
        # Pool gone — rebuild
        return await build_suggestion_pool(user_id, candidate_resume, queries)

    pool = json.loads(pool_raw)
    pool_size = len(pool)
    new_offset = offset + WINDOW_SIZE
    prefetch_triggered = False
    pool_cycling = False

    # Prefetch threshold
    if pool_size > 0 and (new_offset / pool_size) >= PREFETCH_THRESHOLD:
        prefetch_triggered = True
        print(f"[JobSuggestion] 🔄 Prefetch threshold reached ({new_offset}/{pool_size}). Enqueueing scrape...")
        try:
            from app.core.worker import redis_settings
            from arq import create_pool
            arq_redis = await create_pool(redis_settings)
            for q in queries[:3]:  # top 3 queries
                await arq_redis.enqueue_job('collect_jobs_for_query', q, candidate_resume.location or "")
            await arq_redis.close()
        except Exception as e:
            print(f"[JobSuggestion] Failed to enqueue prefetch: {e}")

    # Regen threshold — cycle back and fire background LLM regen
    if new_offset >= pool_size:
        pool_cycling = True
        new_offset = 0
        print("[JobSuggestion] ♻️ Pool exhausted. Cycling from start + triggering background query regen.")
        try:
            from app.modules.jobs.services.query_service import refresh_resume_job_queries
            asyncio.create_task(refresh_resume_job_queries(resume_id, candidate_resume))
        except Exception as e:
            print(f"[JobSuggestion] Background regen failed to start: {e}")

    try:
        await r.set(_offset_key(user_id), new_offset)
    except Exception:
        pass
    finally:
        await r.aclose()

    window = pool[new_offset: new_offset + WINDOW_SIZE]
    return {
        "jobs": window,
        "jobs_seen": min(new_offset + WINDOW_SIZE, pool_size),
        "pool_total": pool_size,
        "prefetch_triggered": prefetch_triggered,
        "pool_cycling": pool_cycling,
    }


def invalidate_pool(user_id: str):
    """Synchronous helper — call from within asyncio.to_thread contexts to delete pool cache."""
    import redis as sync_redis
    from app.core.config import settings
    try:
        r = sync_redis.from_url(settings.REDIS_URL)
        r.delete(_pool_key(user_id), _offset_key(user_id))
        r.close()
    except Exception as e:
        print(f"[JobSuggestion] Pool invalidation failed: {e}")


async def async_invalidate_pool(user_id: str):
    """Async version of pool invalidation."""
    try:
        r = await _get_redis()
        await r.delete(_pool_key(user_id), _offset_key(user_id))
        await r.aclose()
    except Exception as e:
        print(f"[JobSuggestion] Pool invalidation failed: {e}")
