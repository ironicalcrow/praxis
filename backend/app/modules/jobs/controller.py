from typing import Optional, Any
import asyncio
import json
from datetime import datetime
import uuid

import numpy as np
import redis.asyncio as aioredis

from app.core.config import settings
from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.jobs.services.fit_scorer import compute_fit_score
from app.schemas import JobSchema, ResumeSchema, FitScoreResponse, JobRequirementProfile

from app.providers import JSearchScraper
from app.modules.jobs.services.deduplicator import deduplicate_raw_jobs
from app.modules.jobs.models import Job, JobQuery, UserPreference
from app.core.session import SessionLocal
from app.core.llm_caller import embed_text

FIT_SCORE_CACHE_TTL = 21600  # 6 hours



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


def fast_map_db_to_schema(db_job: Job) -> JobSchema:
    return JobSchema(
        id=db_job.id,
        external_id=db_job.external_id,
        provider_id=db_job.provider_id,
        title=db_job.title,
        company_name=db_job.company_name,
        company_website=db_job.company_website,
        publisher=db_job.publisher,
        location=db_job.location,
        is_remote=db_job.is_remote,
        posted_at=db_job.posted_at,
        deadline=db_job.deadline,
        salary=db_job.salary,
        experience_level=db_job.experience_level,
        apply_urls=db_job.apply_urls or [],
        description=db_job.description,
        skills_and_technologies=db_job.skills_and_technologies or [],
        responsibilities=db_job.responsibilities or [],
        qualifications=db_job.qualifications or [],
        benefits=db_job.benefits or [],
        job_types=db_job.job_types or [],
        metadata=db_job.job_metadata or {},
    )


async def _compute_fit_score_with_cache(
    user_id: str,
    job_id: str,
    job_embedding,
    profile: JobRequirementProfile,
    candidate: ResumeSchema,
    add_reasoning: bool = True,
) -> FitScoreResponse:
    cache_key = f"fit_score:{user_id}:{job_id}"

    r_fit = aioredis.from_url(settings.REDIS_URL)
    try:
        cached_raw = await r_fit.get(cache_key)
        if cached_raw:
            print(f"[FitScore] Cache HIT user={user_id} job={job_id}")
            return FitScoreResponse(**json.loads(cached_raw))
    except Exception:
        pass
    finally:
        await r_fit.aclose()

    semantic_sim = None
    if job_embedding:
        def _fetch_resume_vec():
            from app.modules.CV.models import Resume
            with SessionLocal() as db:
                resume = db.query(Resume).filter(Resume.user_id == user_id).first()
                return list(resume.embedding) if resume and resume.embedding is not None else None
        resume_vec = await asyncio.to_thread(_fetch_resume_vec)
        if resume_vec:
            jv = np.array(job_embedding)
            rv = np.array(resume_vec)
            denom = np.linalg.norm(rv) * np.linalg.norm(jv)
            if denom > 1e-9:
                semantic_sim = max(0.0, min(1.0, float(np.dot(rv, jv) / denom)))

    result = await compute_fit_score(
        profile=profile, candidate=candidate,
        semantic_similarity=semantic_sim, add_reasoning=add_reasoning,
    )

    r_fit2 = aioredis.from_url(settings.REDIS_URL)
    try:
        await r_fit2.setex(cache_key, FIT_SCORE_CACHE_TTL, result.model_dump_json())
    except Exception:
        pass
    finally:
        await r_fit2.aclose()

    return result


async def search_live_jobs(
    query: str,
    user_id: uuid.UUID,
    resume_id: str,
    location: Optional[str] = None,
    page: int = 1,
    num_pages: int = 1,
    country: str = "bd",
) -> list[JobSchema]:
    # 1. Fetch UserPreference for location context
    def fetch_prefs():
        with SessionLocal() as db:
            return db.query(UserPreference).filter(UserPreference.user_id == user_id).first()

    prefs = await asyncio.to_thread(fetch_prefs)
    target_loc = location or country or "Any"

    def manage_queries():
        with SessionLocal() as db:
            from app.modules.jobs.services.query_service import _get_or_create_search_query
            from app.modules.jobs.models import SearchQuery

            sq_id = _get_or_create_search_query(db, query, target_loc)
            sq = db.query(SearchQuery).filter(SearchQuery.id == sq_id).first()

            is_stale = True
            if sq and sq.last_run_at:
                age_s = (datetime.utcnow() - sq.last_run_at).total_seconds()
                if age_s < 86400:
                    is_stale = False
                    print(f"[LiveSearch] Cache HOT for '{query}' (age {age_s/3600:.1f}h). Bypassing API.")
                else:
                    print(f"[LiveSearch] Cache STALE for '{query}'. Will hit API.")
            else:
                print(f"[LiveSearch] Brand new query '{query}'.")

            user_queries = (
                db.query(JobQuery)
                .filter(JobQuery.resume_id == resume_id)
                .order_by(JobQuery.priority.desc(), JobQuery.added_at.asc())
                .all()
            )

            existing = next((q for q in user_queries if q.search_query_id == sq_id), None)
            if not existing:
                if len(user_queries) >= 10:
                    evicted = user_queries[-1]
                    print(f"[ManualSearch] Evicting lowest-priority query '{evicted.query}'.")
                    db.delete(evicted)

                db.add(JobQuery(
                    id=uuid.uuid4(),
                    resume_id=str(resume_id),
                    search_query_id=sq_id,
                    query=query,
                    reason="user searched",
                    priority=10,
                ))
            else:
                existing.priority = 10
                existing.added_at = datetime.utcnow()

            manual_count = sum(1 for q in user_queries if q.reason == "user searched")
            trigger_refresh = manual_count > 5
            if trigger_refresh:
                print(f"[ManualSearch] Manual search threshold hit ({manual_count}). Triggering query refresh.")

            db.commit()
            return is_stale, sq_id, trigger_refresh

    is_stale, sq_id, trigger_refresh = await asyncio.to_thread(manage_queries)

    if trigger_refresh:
        try:
            from app.modules.CV.route import fetch_resume_from_db as fetch_cv
            resume_obj_data = await asyncio.to_thread(fetch_cv, user_id)
            if resume_obj_data:
                from app.modules.jobs.services.query_service import refresh_resume_job_queries
                asyncio.create_task(
                    refresh_resume_job_queries(str(resume_id), ResumeSchema(**resume_obj_data))
                )
        except Exception as e:
            print(f"[ManualSearch] Auto-refresh failed to start: {e}")

    if is_stale:
        try:
            from app.core.worker import redis_settings
            from arq import create_pool
            redis = await create_pool(redis_settings)
            await redis.enqueue_job('collect_jobs_for_query', query, target_loc, sq_id)
            await redis.close()
            print(f"[LiveSearch] Enqueued 'collect_jobs_for_query' for '{query}'.")
        except Exception as e:
            print(f"[LiveSearch] Failed to enqueue ARQ job: {e}")

        # Only invalidate pool when new data is actually being fetched
        try:
            from app.modules.jobs.services.job_suggestion import async_invalidate_pool
            await async_invalidate_pool(str(user_id))
        except Exception as e:
            print(f"[LiveSearch] Pool invalidation failed: {e}")

    # Concurrent: pgvector DB search + live JSearch
    try:
        vector = await embed_text(query)
    except Exception as e:
        print(f"[LiveSearch] Query embedding failed: {e}. DB search will be skipped.")
        vector = None

    def search_db():
        with SessionLocal() as db:
            if vector is None:
                return []
            try:
                q = db.query(Job).filter(Job.embedding.is_not(None))
                if location:
                    q = q.filter(Job.location.ilike(f"%{location}%"))
                if country and country != "any":
                    q = q.filter(Job.location.ilike(f"%{country}%"))
                limit = num_pages * 10
                offset = (page - 1) * 10
                return q.order_by(Job.embedding.cosine_distance(vector)).offset(offset).limit(limit).all()
            except Exception as e:
                print(f"[LiveSearch] DB search error: {e}")
                return []

    async def fetch_live():
        if page == 1 and is_stale:
            try:
                scraper = JSearchScraper()
                live_loc = location if location else (country if country != "any" else "")
                return await scraper.search_jobs(query, location=live_loc, limit=10)
            except Exception as e:
                print(f"[LiveSearch] Live fetch failed: {e}")
        return []

    db_jobs, live_raw = await asyncio.gather(
        asyncio.to_thread(search_db),
        fetch_live(),
    )

    final_schemas: list[JobSchema] = []

    if live_raw:
        import redis.asyncio as aioredis
        from app.core.config import settings
        r = aioredis.from_url(settings.REDIS_URL)
        db_external_ids = {j.external_id for j in db_jobs if j.external_id}
        try:
            from app.modules.jobs.services.jsearch_parser import parse_jsearch_to_schema
            for r_job in live_raw:
                if r_job.job_id in db_external_ids:
                    continue
                try:
                    live_id = str(uuid.uuid4())
                    await r.setex(f"temp_job:{live_id}", 7200, r_job.model_dump_json())
                    parsed = parse_jsearch_to_schema(r_job)
                    parsed.id = live_id
                    final_schemas.append(parsed)
                except Exception:
                    pass
        finally:
            await r.aclose()

    for j in db_jobs:
        final_schemas.append(fast_map_db_to_schema(j))

    return final_schemas[:num_pages * 10]


async def get_job_detail(job_id: str, current_user: Any = None) -> JobSchema | None:
    def fetch():
        with SessionLocal() as db:
            return db.query(Job).filter(
                (Job.external_id == job_id) | (Job.id == job_id)
            ).first()

    db_job = await asyncio.to_thread(fetch)

    if db_job:
        schema = JobSchema(
            id=db_job.id,
            external_id=db_job.external_id,
            provider_id=db_job.provider_id,
            title=db_job.title,
            company_name=db_job.company_name,
            company_website=db_job.company_website,
            publisher=db_job.publisher,
            location=db_job.location,
            is_remote=db_job.is_remote,
            posted_at=db_job.posted_at,
            deadline=db_job.deadline,
            salary=db_job.salary,
            experience_level=db_job.experience_level,
            apply_urls=db_job.apply_urls or [],
            description=db_job.description,
            skills_and_technologies=db_job.skills_and_technologies or [],
            responsibilities=db_job.responsibilities or [],
            qualifications=db_job.qualifications or [],
            benefits=db_job.benefits or [],
            job_types=db_job.job_types or [],
            metadata=db_job.job_metadata or {},
        )

        if current_user:
            try:
                resume_data = await asyncio.to_thread(fetch_resume_from_db, current_user.id)
                candidate_resume = ResumeSchema(**resume_data)
                profile = _job_to_profile(db_job)
                schema.fit_score = await _compute_fit_score_with_cache(
                    user_id=str(current_user.id),
                    job_id=str(schema.id),
                    job_embedding=db_job.embedding,
                    profile=profile,
                    candidate=candidate_resume,
                )
            except Exception as e:
                print(f"[JobDetail] Fit score (DB path) failed: {e}")

        return schema

    # Not in DB — check live Redis cache
    import json
    import redis.asyncio as aioredis
    from app.core.config import settings
    from app.providers.schemas import RawScrapedJob
    from app.modules.jobs.services.jsearch_parser import parse_jsearch_to_schema

    r = aioredis.from_url(settings.REDIS_URL)
    try:
        raw_data_str = await r.get(f"temp_job:{job_id}")
    except Exception:
        raw_data_str = None
    finally:
        await r.aclose()

    if not raw_data_str:
        raise ValueError(f"Job {job_id} not found in DB or live cache.")

    print(f"[JobDetail] Found live job {job_id} in Redis cache. Parsing...")
    raw_job = RawScrapedJob(**json.loads(raw_data_str))
    parsed_schema = parse_jsearch_to_schema(raw_job)

    # Embed FIRST (blocking) so the saved row is immediately searchable via pgvector
    embedding_input = f"{parsed_schema.title} {parsed_schema.company_name} "
    if parsed_schema.skills_and_technologies:
        embedding_input += "Skills: " + ", ".join(parsed_schema.skills_and_technologies) + ". "
    if parsed_schema.description:
        embedding_input += parsed_schema.description[:400]
    try:
        embedding_vector = await embed_text(embedding_input)
        print(f"[JobDetail] ✅ Embedding computed ({len(embedding_vector)} dims).")
    except Exception as e:
        print(f"[JobDetail] Embedding failed: {e}. Saving without vector.")
        embedding_vector = None

    def save_live_job():
        with SessionLocal() as db:
            # Dedup: job may already exist if ARQ worker scraped it concurrently
            existing = db.query(Job).filter(Job.external_id == parsed_schema.external_id).first()
            if existing:
                if embedding_vector is not None and existing.embedding is None:
                    existing.embedding = embedding_vector
                    db.commit()
                return existing.id

            new_job = Job(
                id=job_id,
                external_id=parsed_schema.external_id,
                provider_id=parsed_schema.provider_id,
                title=parsed_schema.title,
                company_name=parsed_schema.company_name,
                company_website=parsed_schema.company_website,
                publisher=parsed_schema.publisher,
                location=parsed_schema.location,
                is_remote=parsed_schema.is_remote,
                posted_at=parsed_schema.posted_at,
                deadline=parsed_schema.deadline,
                salary=parsed_schema.salary,
                experience_level=parsed_schema.experience_level,
                description=parsed_schema.description,
                skills_and_technologies=parsed_schema.skills_and_technologies,
                responsibilities=parsed_schema.responsibilities,
                qualifications=parsed_schema.qualifications,
                benefits=parsed_schema.benefits,
                apply_urls=parsed_schema.apply_urls,
                job_types=parsed_schema.job_types,
                job_metadata=parsed_schema.metadata,
                embedding=embedding_vector,
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            return new_job.id

    try:
        saved_id = await asyncio.to_thread(save_live_job)
        parsed_schema.id = saved_id
        print(f"[JobDetail] Live job {job_id} persisted to DB (with embedding).")
    except Exception as e:
        print(f"[JobDetail] Failed to persist live job: {e}")

    if current_user:
        try:
            resume_data = await asyncio.to_thread(fetch_resume_from_db, current_user.id)
            candidate_resume = ResumeSchema(**resume_data)
            profile = JobRequirementProfile(
                summary=parsed_schema.description or "",
                description=parsed_schema.description or "",
                required_skills=parsed_schema.skills_and_technologies or [],
                preferred_skills=[],
                tools_and_technologies=parsed_schema.skills_and_technologies or [],
                soft_skills=[],
                responsibilities=parsed_schema.responsibilities or [],
                qualifications=parsed_schema.qualifications or [],
            )
            parsed_schema.fit_score = await _compute_fit_score_with_cache(
                user_id=str(current_user.id),
                job_id=str(parsed_schema.id),
                job_embedding=embedding_vector,
                profile=profile,
                candidate=candidate_resume,
            )
        except Exception as e:
            print(f"[JobDetail] Fit score failed: {e}")

    return parsed_schema


async def calculate_job_fit_score(job_id: str, current_user) -> FitScoreResponse:
    job_schema = await get_job_detail(job_id)
    resume_data = await asyncio.to_thread(fetch_resume_from_db, current_user.id)
    candidate_resume = ResumeSchema(**resume_data)

    profile = JobRequirementProfile(
        summary=job_schema.description or "",
        description=job_schema.description or "",
        required_skills=job_schema.skills_and_technologies or [],
        preferred_skills=[],
        tools_and_technologies=job_schema.skills_and_technologies or [],
        methodologies=[],
        soft_skills=[],
        responsibilities=job_schema.responsibilities or [],
        qualifications=job_schema.qualifications or [],
        benefits=job_schema.benefits or [],
        required_experience_years=0,
        seniority_level="",
        job_function="",
        industry="",
        work_arrangement="Remote" if job_schema.is_remote else "Onsite",
        education_requirements=[],
        important_context=[],
    )

    def fetch_job_embedding():
        with SessionLocal() as db:
            j = db.query(Job).filter(
                (Job.id == str(job_schema.id)) | (Job.external_id == job_id)
            ).first()
            return list(j.embedding) if j and j.embedding is not None else None

    job_embedding = await asyncio.to_thread(fetch_job_embedding)

    return await _compute_fit_score_with_cache(
        user_id=str(current_user.id),
        job_id=str(job_schema.id or job_id),
        job_embedding=job_embedding,
        profile=profile,
        candidate=candidate_resume,
    )


async def get_user_preferences(user_id: str) -> dict:
    def fetch():
        with SessionLocal() as db:
            pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
            if not pref:
                return {"id": "", "user_id": str(user_id), "job_types": []}
            return {
                "id": str(pref.id),
                "user_id": str(pref.user_id),
                "job_types": pref.job_types or [],
            }

    return await asyncio.to_thread(fetch)


async def update_user_preferences(user_id: str, data: dict) -> dict:
    """Update preferences. Generates preference embedding best-effort (never blocks the save)."""

    def update_db():
        with SessionLocal() as db:
            pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
            job_types = [v.value if hasattr(v, 'value') else v for v in (data.get("job_types") or [])]
            if not pref:
                pref = UserPreference(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    job_types=job_types,
                )
                db.add(pref)
            else:
                if "job_types" in data and data["job_types"] is not None:
                    pref.job_types = job_types
            db.commit()
            db.refresh(pref)
            return {
                "id": str(pref.id),
                "user_id": str(pref.user_id),
                "job_types": pref.job_types or [],
            }

    result = await asyncio.to_thread(update_db)

    # Generate preference embedding — best-effort, never fails the response
    try:
        job_types = [v.value if hasattr(v, 'value') else v for v in (data.get("job_types") or [])]
        if job_types:
            pref_text = "Preferred job types: " + ", ".join(job_types)
            pref_vector = await embed_text(pref_text)

            def save_embedding():
                with SessionLocal() as db:
                    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
                    if pref:
                        pref.preference_embedding = pref_vector
                        db.commit()

            await asyncio.to_thread(save_embedding)
            print(f"[Preferences] ✅ Preference embedding saved for user {user_id}.")
    except Exception as e:
        print(f"[Preferences] ⚠️ Embedding skipped: {e}. Preferences saved without vector signal.")

    # Invalidate suggestion pool so next GET rebuilds with updated preference vector
    try:
        from app.modules.jobs.services.job_suggestion import async_invalidate_pool
        await async_invalidate_pool(str(user_id))
    except Exception as e:
        print(f"[Preferences] Pool invalidation failed: {e}")

    return result
