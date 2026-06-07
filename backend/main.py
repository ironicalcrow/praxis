from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.session import get_engine
from app.models import (
    Base,
    User,
    Resume,
    ResumeSkill,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeCertification,
    ChatConversation,
    ChatSession,
    ChatMessage,
    Roadmap,
    RoadmapPhase,
    RoadmapMilestone,
    Goal,
    Notification,
)
from app.modules.jobs.models import JobQuery

app = FastAPI(title="PRAXIS")


@app.on_event("startup")
def on_startup():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

from app.modules.notifications.route import ws_notifications
app.add_api_websocket_route("/ws/notifications", ws_notifications)


@app.get("/")
def root():
    return {"message": "Praxis server is running"}


@app.get("/health")
async def health():
    """Dependency health check — no auth required."""
    from sqlalchemy import text

    status = {
        "db": "ok",
        "redis": "ok",
        "status": "healthy",
    }

    try:
        from app.core.session import SessionLocal

        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

    except Exception as e:
        status["db"] = f"error: {e}"
        status["status"] = "degraded"

    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.REDIS_URL)

        await r.ping()
        await r.aclose()

    except Exception as e:
        status["redis"] = f"error: {e}"
        status["status"] = "degraded"

    return status