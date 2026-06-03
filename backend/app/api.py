from fastapi import APIRouter

from app.modules.jobs.route import router as jobs_router
from app.modules.fit_score.route import router as fit_score_router

api_router = APIRouter(prefix="/api")

api_router.include_router(jobs_router)
api_router.include_router(fit_score_router)