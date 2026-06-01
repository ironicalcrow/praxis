from fastapi import APIRouter
from app.modules.jobs.route import router as jobs_router

api_router = APIRouter(prefix="/api")

api_router.include_router(jobs_router)
