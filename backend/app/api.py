from fastapi import APIRouter

from app.modules.jobs.route import router as jobs_router
from app.modules.CV.route import router as cv_router
from app.modules.auth.route import router as auth_router
from app.modules.application.route import router as application_router
from app.modules.chat.route import router as chat_router
from app.modules.roadmap.route import router as roadmap_router
from app.modules.goals.route import router as goals_router
from app.modules.notifications.route import router as notifications_router
from app.modules.cover_letter.route import router as cover_letter_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(cv_router, prefix="/cv", tags=["CV"])
api_router.include_router(jobs_router)
api_router.include_router(application_router)
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(roadmap_router, prefix="/roadmap", tags=["Roadmap"])
api_router.include_router(goals_router, prefix="/goals", tags=["Goals"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(cover_letter_router, prefix="/cover-letter", tags=["Cover Letter"])
