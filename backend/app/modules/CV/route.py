import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.modules.CV.cv import resume_parser
from app.modules.CV.db_service import save_resume_to_db
from app.modules.auth.dependency import get_current_user
from fastapi import Depends, HTTPException
from app.core.supabase import supabase_admin


router = APIRouter()


UPLOAD_DIR = "uploads"

Path(UPLOAD_DIR).mkdir(exist_ok=True)


@router.post("/upload-cv")
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
    
@router.get("/my-cv")
async def get_my_cv(current_user=Depends(get_current_user)):
    """
    Fetch logged-in user's CV from database.
    Requires access token.
    """

    try:
        resume_response = (
            supabase_admin
            .table("resumes")
            .select("*")
            .eq("user_id", current_user.id)
            .single()
            .execute()
        )

        if not resume_response.data:
            raise HTTPException(
                status_code=404,
                detail="No CV found for this user"
            )

        resume = resume_response.data
        resume_id = resume["id"]

        skills_response = (
            supabase_admin
            .table("resume_skills")
            .select("skill")
            .eq("resume_id", resume_id)
            .execute()
        )

        education_response = (
            supabase_admin
            .table("resume_education")
            .select("degree, institution, year, gpa")
            .eq("resume_id", resume_id)
            .execute()
        )

        experience_response = (
            supabase_admin
            .table("resume_experience")
            .select("role, organization, description")
            .eq("resume_id", resume_id)
            .execute()
        )

        projects_response = (
            supabase_admin
            .table("resume_projects")
            .select("name, description, technology")
            .eq("resume_id", resume_id)
            .execute()
        )

        certifications_response = (
            supabase_admin
            .table("resume_certifications")
            .select("certification")
            .eq("resume_id", resume_id)
            .execute()
        )

        return {
            "success": True,
            "data": {
                "id": resume["id"],
                "user_id": resume["user_id"],
                "name": resume["name"],
                "email": resume["email"],
                "phone": resume["phone"],
                "location": resume["location"],
                "years_of_experience": resume["years_of_experience"],
                "raw_text": resume["raw_text"],
                "skills": [
                    item["skill"]
                    for item in skills_response.data
                ],
                "education": education_response.data,
                "experience": experience_response.data,
                "projects": projects_response.data,
                "certifications": [
                    item["certification"]
                    for item in certifications_response.data
                ],
                "created_at": resume["created_at"],
                "updated_at": resume["updated_at"],
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )