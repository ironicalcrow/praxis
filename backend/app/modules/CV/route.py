import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.modules.CV.cv import resume_parser
from app.modules.CV.db_service import save_resume_to_db, fetch_resume_from_db
from app.modules.CV.schemas import ResumeSchema, ResumeResponse, UploadCVResponse
from app.modules.auth.dependency import get_current_user


router = APIRouter()


UPLOAD_DIR = "uploads"

Path(UPLOAD_DIR).mkdir(exist_ok=True)


@router.post("/upload-cv", response_model=UploadCVResponse)
async def upload_cv(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    Upload CV endpoint.
    Requires access token.
    """

    allowed_extensions = [
        ".pdf",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
    ]

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format",
        )

    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = f"{UPLOAD_DIR}/{unique_filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        parsed_resume = await resume_parser(file_path)

        db_result = save_resume_to_db(
            parsed_resume=parsed_resume,
            user_id=current_user.id
        )

        return {
            "success": True,
            "message": "CV uploaded, parsed, and saved successfully",
            "resume_id": db_result["resume_id"],
            "data": parsed_resume,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    
@router.get("/my-cv", response_model=ResumeResponse)
async def get_my_cv(current_user=Depends(get_current_user)):
    """
    Fetch logged-in user's CV from database.
    Requires access token.
    """

    return fetch_resume_from_db(current_user.id)