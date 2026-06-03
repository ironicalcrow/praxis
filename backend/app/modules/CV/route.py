import shutil
import uuid

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.modules.CV.cv import resume_parser


router = APIRouter()

UPLOAD_DIR = "uploads"

Path(UPLOAD_DIR).mkdir(exist_ok=True)


@router.post("/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload CV endpoint.
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

        parsed_resume =await resume_parser(file_path)

        return {
            "success": True,
            "data": parsed_resume,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )