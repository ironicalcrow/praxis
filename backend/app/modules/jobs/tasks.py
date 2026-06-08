import asyncio
from datetime import datetime, timedelta

from app.core.session import SessionLocal
from app.modules.jobs.models import JobQuery, Job
from app.providers import JSearchScraper
from app.modules.jobs.services.deduplicator import deduplicate_raw_jobs
from app.modules.jobs.services.jsearch_parser import parse_jsearch_to_schema
from app.core.llm_caller import embed_text
import redis.asyncio as aioredis
from app.core.config import settings

# Global semaphore — shared across ALL concurrent ARQ tasks so we never exceed
# Jina's free-tier concurrency limit of 2 simultaneous embedding requests.
_embedding_sem = asyncio.Semaphore(2)

SEEN_JOB_TTL = timedelta(hours=48)


def _save_job_to_db(schema, vector, search_query_id):
    """Sync DB upsert for a single parsed job. Call via asyncio.to_thread."""
    with SessionLocal() as db:
        from app.modules.jobs.models import SearchQuery
        existing = db.query(Job).filter(
            Job.external_id == schema.external_id,
            Job.provider_id == schema.provider_id,
        ).first()

        if existing:
            existing.updated_at = datetime.utcnow()
            if vector is not None:
                existing.embedding = vector
            job_to_link = existing
        else:
            new_job = Job(
                external_id=schema.external_id,
                provider_id=schema.provider_id,
                title=schema.title,
                company_name=schema.company_name,
                location=schema.location,
                description=schema.description,
                salary=schema.salary,
                experience_level=schema.experience_level,
                posted_at=schema.posted_at,
                deadline=schema.deadline,
                publisher=schema.publisher,
                company_website=schema.company_website,
                skills_and_technologies=schema.skills_and_technologies,
                responsibilities=schema.responsibilities,
                qualifications=schema.qualifications,
                benefits=schema.benefits,
                apply_urls=schema.apply_urls,
                job_types=schema.job_types,
                is_remote=schema.is_remote,
                embedding=vector,
            )
            db.add(new_job)
            job_to_link = new_job

        if search_query_id:
            sq = db.query(SearchQuery).filter(SearchQuery.id == search_query_id).first()
            if sq and sq not in job_to_link.search_queries:
                job_to_link.search_queries.append(sq)

        db.commit()


async def _process_and_save_job(raw_job, r, sem) -> None:
    """Parse, embed, and persist one scraped job. Idempotent via Redis dedup key."""
    unique_key = f"seen_job:{raw_job.provider_id}:{raw_job.job_id}"
    try:
        if await r.exists(unique_key):
            return
    except Exception:
        pass  # Redis down — proceed anyway

    async with sem:
        try:
            job_schema = parse_jsearch_to_schema(raw_job)

            embedding_input = f"{job_schema.title} {job_schema.company_name} "
            if job_schema.skills_and_technologies:
                embedding_input += "Skills: " + ", ".join(job_schema.skills_and_technologies) + ". "
            if job_schema.description:
                embedding_input += job_schema.description[:300]

            try:
                embedding_vector = await embed_text(embedding_input)
            except Exception as e:
                print(f"[Worker] ⚠️ Embedding failed for '{job_schema.title}': {e}. Saving without vector.")
                embedding_vector = None

            await asyncio.to_thread(_save_job_to_db, job_schema, embedding_vector, raw_job.search_query_id)
            print(f"[Worker] ✅ Saved: '{job_schema.title}' @ '{job_schema.company_name}'")

            try:
                await r.set(unique_key, "1", ex=SEEN_JOB_TTL)
            except Exception:
                pass

        except Exception as e:
            print(f"[Worker] Error processing job {raw_job.job_id}: {e}")


async def collect_jobs(ctx):
    """Cron task: refresh all stale SearchQuery records."""
    print("[Worker] ⏰ Starting 'collect_jobs' CRON cycle...")

    def fetch_unique_queries():
        with SessionLocal() as db:
            from app.modules.jobs.models import SearchQuery
            one_day_ago = datetime.utcnow() - timedelta(hours=24)
            stale = db.query(SearchQuery).filter(
                (SearchQuery.last_run_at.is_(None)) | (SearchQuery.last_run_at < one_day_ago)
            ).all()
            return [(sq.id, sq.query, sq.location) for sq in stale]

    tasks = await asyncio.to_thread(fetch_unique_queries)
    if not tasks:
        print("[Worker] 🟢 No stale queries. CRON cycle skipped.")
        return

    print(f"[Worker] Found {len(tasks)} stale SearchQuery records.")
    jsearch = JSearchScraper()

    scrape_tasks = []
    for sq_id, query, location in tasks:
        loc = location or "Bangladesh"
        print(f"[Worker] Scraping: '{query}' in '{loc}'")
        scrape_tasks.append((sq_id, jsearch.search_jobs(query, location=loc, limit=200)))

    results = await asyncio.gather(*(t[1] for t in scrape_tasks), return_exceptions=True)

    def update_last_run():
        with SessionLocal() as db:
            from app.modules.jobs.models import SearchQuery
            for i, res in enumerate(results):
                if not isinstance(res, Exception):
                    sq = db.query(SearchQuery).filter(SearchQuery.id == scrape_tasks[i][0]).first()
                    if sq:
                        sq.last_run_at = datetime.utcnow()
            db.commit()

    await asyncio.to_thread(update_last_run)

    all_raw_jobs = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"[Worker] Scrape error for query index {i}: {res}")
            continue
        sq_id = scrape_tasks[i][0]
        for rj in res:
            rj.search_query_id = sq_id
        all_raw_jobs.extend(res)

    # Remote fallback if a particular query returned nothing
    for i, res in enumerate(results):
        if isinstance(res, Exception) or len(res) > 0:
            continue
        sq_id, query, _ = tasks[i]
        print(f"[Worker] No results for '{query}'. Falling back to global remote search...")
        try:
            fallback = await jsearch.search_jobs(query, location="", limit=50)
            for rj in fallback:
                rj.search_query_id = sq_id
            all_raw_jobs.extend(fallback)
            print(f"[Worker] Fallback returned {len(fallback)} remote jobs for '{query}'.")
        except Exception as e:
            print(f"[Worker] Fallback failed for '{query}': {e}")

    unique_jobs = deduplicate_raw_jobs(all_raw_jobs)
    print(f"[Worker] Deduplicated to {len(unique_jobs)} unique jobs.")

    r = aioredis.from_url(settings.REDIS_URL)
    await asyncio.gather(*(_process_and_save_job(job, r, _embedding_sem) for job in unique_jobs))
    try:
        await r.aclose()
    except Exception:
        pass
    print("[Worker] ✅ Job Collection Cycle Complete!")


async def collect_jobs_for_query(
    ctx,
    query: str,
    location: str | None = None,
    search_query_id: str | None = None,
):
    """ARQ task: instantly collect jobs for a specific query (manual search / query generation)."""
    print(f"[Worker] Instant Queue: '{query}' in '{location or 'Any'}'")
    jsearch = JSearchScraper()
    loc = location or "Bangladesh"

    results = await asyncio.gather(
        jsearch.search_jobs(query, location=loc, limit=200),
        return_exceptions=True,
    )

    all_raw_jobs = []
    for res in results:
        if not isinstance(res, Exception):
            for rj in res:
                rj.search_query_id = search_query_id
            all_raw_jobs.extend(res)
        else:
            print(f"[Worker] Instant Queue scrape error: {res}")

    # Remote fallback
    if len(all_raw_jobs) == 0:
        print(f"[Worker] No results for '{query}' in '{loc}'. Falling back to global remote search...")
        try:
            fallback = await jsearch.search_jobs(query, location="", limit=50)
            for rj in fallback:
                rj.search_query_id = search_query_id
            all_raw_jobs.extend(fallback)
            print(f"[Worker] Fallback returned {len(fallback)} remote jobs.")
        except Exception as e:
            print(f"[Worker] Fallback failed: {e}")

    unique_jobs = deduplicate_raw_jobs(all_raw_jobs)
    print(f"[Worker] Instant Queue: {len(unique_jobs)} unique jobs after dedup.")

    r = aioredis.from_url(settings.REDIS_URL)
    await asyncio.gather(*(_process_and_save_job(job, r, _embedding_sem) for job in unique_jobs))
    try:
        await r.aclose()
    except Exception:
        pass
    print(f"[Worker] Instant Queue: Finished for '{query}'!")


async def clean_expired_jobs(ctx):
    """TTL cleanup: delete jobs older than 48h and orphaned SearchQueries."""
    print("[Worker] Running TTL Cleanup...")

    def purge():
        with SessionLocal() as db:
            from app.modules.jobs.models import SearchQuery, JobQuery

            active_sq_ids = db.query(JobQuery.search_query_id).filter(
                JobQuery.search_query_id.is_not(None)
            ).distinct().all()
            active_ids = {r[0] for r in active_sq_ids}

            if active_ids:
                deleted_sq = db.query(SearchQuery).filter(
                    SearchQuery.id.notin_(active_ids)
                ).delete(synchronize_session=False)
            else:
                deleted_sq = db.query(SearchQuery).delete(synchronize_session=False)

            two_days_ago = datetime.utcnow() - timedelta(hours=48)
            deleted_jobs = db.query(Job).filter(Job.updated_at < two_days_ago).delete(
                synchronize_session=False
            )
            db.commit()
            return deleted_sq, deleted_jobs

    deleted_sq, deleted_jobs = await asyncio.to_thread(purge)
    print(f"[Worker] Garbage Collected {deleted_sq} stale queries. Deleted {deleted_jobs} expired jobs.")
