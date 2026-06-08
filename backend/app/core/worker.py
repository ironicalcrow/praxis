from arq.connections import RedisSettings
from app.core.config import settings
from arq import cron
from app.modules.jobs.tasks import collect_jobs, clean_expired_jobs, collect_jobs_for_query


async def prune_chat_messages(ctx):
    """
    Weekly CRON: delete raw messages from completed sessions
    older than the last 2 per conversation. Session rows + summaries kept forever.
    """
    from app.core.session import SessionLocal
    from app.modules.chat.models import ChatConversation
    from app.modules.chat.db_service import prune_old_messages

    total_deleted = 0
    with SessionLocal() as db:
        conversations = db.query(ChatConversation).all()
        for conv in conversations:
            try:
                deleted = prune_old_messages(db, conv.id, keep_sessions=2)
                total_deleted += deleted
            except Exception as e:
                print(f"[Worker] Prune failed for conversation {conv.id}: {e}")
    print(f"[Worker] Chat message prune complete — {total_deleted} messages deleted.")

# Parse the Upstash REDIS_URL directly from config using ARQ's built in DSN parser
redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

# Import all models to ensure SQLAlchemy mapper resolves string relationships (like 'Application' and 'Resume')
import app.models
import app.modules.application.models
import app.modules.auth.models
import app.modules.CV.models
import app.modules.jobs.models

async def startup(ctx):
    print("Worker starting up...")

async def shutdown(ctx):
    print("Worker shutting down...")

class WorkerSettings:
    functions = [collect_jobs, clean_expired_jobs, collect_jobs_for_query, prune_chat_messages]
    cron_jobs = [
        # Collect jobs every 6 hours (00:00, 06:00, 12:00, 18:00)
        cron(collect_jobs, hour={0, 6, 12, 18}, minute=0),
        # TTL Cleanup runs once daily at 01:00 AM
        cron(clean_expired_jobs, hour=1, minute=0),
        # Chat message prune runs weekly on Sunday at 02:00 AM
        cron(prune_chat_messages, weekday=6, hour=2, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings
    job_timeout = 900 # 15 minutes to allow for heavy LLM processing
