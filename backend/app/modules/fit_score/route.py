from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.dependency import get_current_user
from app.modules.fit_score.service import calculate_job_fit_score
from app.modules.jobs.providers.jsearch import JSearchError
from app.modules.jobs.services.job_profile_extreactor import JobProfileExtractorError
from app.schemas import JobDetailWithFitResponse

router = APIRouter(prefix="/fit-score", tags=["Fit Score"])


@router.post("/jobs/{job_id}", response_model=JobDetailWithFitResponse)
async def get_job_fit_score(
    job_id: str,
    current_user=Depends(get_current_user),
):
    try:
        return await calculate_job_fit_score(
            job_id=job_id,
            current_user=current_user,
        )

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except JobProfileExtractorError as e:
        raise HTTPException(status_code=400, detail=str(e))
