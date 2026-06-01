from fastapi import APIRouter, HTTPException

from app.modules.jobs.providers.jsearch import JSearchError
from app.schemas import JobSearchRequest, JobSearchResponse
from app.modules.jobs.service import search_live_jobs

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/live-search", response_model=JobSearchResponse)
async def live_search_jobs(request: JobSearchRequest):
    try:
        jobs = await search_live_jobs(
            query=request.query,
            location=request.location,
            page=request.page,
            num_pages=request.num_pages,
        )

        return JobSearchResponse(
            query=request.query,
            total=len(jobs),
            jobs=jobs,
        )

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))