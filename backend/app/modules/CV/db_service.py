import uuid
from uuid import UUID as PyUUID, uuid4
from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from app.core.session import get_session, SessionLocal
from app.modules.CV.models import (
    Resume,
    ResumeSkill,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeCertification,
    CVUpload,
)
from app.schemas import ResumeSchema


def parse_user_uuid(user_id: str):
    try:
        return PyUUID(str(user_id))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id. Expected UUID format.",
        )


def save_resume_to_db(parsed_resume: ResumeSchema, user_id: str, file_url: Optional[str] = None):

    db = get_session()

    try:
        user_uuid = parse_user_uuid(user_id)

        existing_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_uuid)
            .first()
        )

        if existing_resume:
            existing_resume.name = parsed_resume.name
            existing_resume.email = parsed_resume.email
            existing_resume.phone = parsed_resume.phone
            existing_resume.location = parsed_resume.location
            existing_resume.country = parsed_resume.country
            existing_resume.years_of_experience = parsed_resume.years_of_experience
            existing_resume.raw_text = parsed_resume.raw_text
            if file_url is not None:
                existing_resume.file_url = file_url

            resume_id = existing_resume.id

            db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume_id).delete()
            db.query(ResumeEducation).filter(ResumeEducation.resume_id == resume_id).delete()
            db.query(ResumeExperience).filter(ResumeExperience.resume_id == resume_id).delete()
            db.query(ResumeProject).filter(ResumeProject.resume_id == resume_id).delete()
            db.query(ResumeCertification).filter(ResumeCertification.resume_id == resume_id).delete()

        else:
            resume_id = str(uuid.uuid4())

            new_resume = Resume(
                id=resume_id,
                user_id=user_uuid,
                name=parsed_resume.name,
                email=parsed_resume.email,
                phone=parsed_resume.phone,
                location=parsed_resume.location,
                country=parsed_resume.country,
                years_of_experience=parsed_resume.years_of_experience,
                raw_text=parsed_resume.raw_text,
                file_url=file_url,
            )

            db.add(new_resume)

        if parsed_resume.skills:
            for skill in parsed_resume.skills:
                skill_obj = ResumeSkill(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    skill=skill,
                )
                db.add(skill_obj)

        if parsed_resume.education:
            for edu in parsed_resume.education:
                edu_obj = ResumeEducation(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    degree=edu.degree,
                    institution=edu.institution,
                    year=edu.year,
                    gpa=edu.gpa,
                )
                db.add(edu_obj)

        if parsed_resume.experience:
            for exp in parsed_resume.experience:
                exp_obj = ResumeExperience(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    role=exp.role,
                    organization=exp.organization,
                    description=exp.description,
                )
                db.add(exp_obj)

        if parsed_resume.projects:
            for project in parsed_resume.projects:
                proj_obj = ResumeProject(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    name=project.name,
                    description=project.description,
                    technology=project.technology,
                )
                db.add(proj_obj)

        if parsed_resume.certifications:
            for cert in parsed_resume.certifications:
                cert_obj = ResumeCertification(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    certification=cert,
                )
                db.add(cert_obj)

        db.commit()

        return {
            "resume_id": resume_id,
            "message": "Resume saved successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database save failed: {str(e)}",
        )

    finally:
        db.close()


def fetch_resume_from_db(user_id: str):

    db = get_session()

    try:
        user_uuid = parse_user_uuid(user_id)

        resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_uuid)
            .first()
        )

        if not resume:
            raise HTTPException(
                status_code=404,
                detail="No CV found for this user",
            )

        skills = (
            db.query(ResumeSkill)
            .filter(ResumeSkill.resume_id == resume.id)
            .all()
        )

        education = (
            db.query(ResumeEducation)
            .filter(ResumeEducation.resume_id == resume.id)
            .all()
        )

        experience = (
            db.query(ResumeExperience)
            .filter(ResumeExperience.resume_id == resume.id)
            .all()
        )

        projects = (
            db.query(ResumeProject)
            .filter(ResumeProject.resume_id == resume.id)
            .all()
        )

        certifications = (
            db.query(ResumeCertification)
            .filter(ResumeCertification.resume_id == resume.id)
            .all()
        )

        return {
            "id": resume.id,
            "user_id": str(resume.user_id),
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "location": resume.location,
            "country": resume.country,
            "years_of_experience": resume.years_of_experience,
            "raw_text": resume.raw_text,
            "skills": [skill.skill for skill in skills],
            "education": [
                {
                    "degree": edu.degree,
                    "institution": edu.institution,
                    "year": edu.year,
                    "gpa": edu.gpa,
                }
                for edu in education
            ],
            "experience": [
                {
                    "role": exp.role,
                    "organization": exp.organization,
                    "description": exp.description,
                }
                for exp in experience
            ],
            "projects": [
                {
                    "name": proj.name,
                    "description": proj.description,
                    "technology": proj.technology,
                }
                for proj in projects
            ],
            "certifications": [
                cert.certification for cert in certifications
            ],
            "file_url": resume.file_url,
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch resume: {str(e)}",
        )

    finally:
        db.close()

def update_resume_embedding(resume_id: str, embedding: list[float]):
    db = get_session()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.embedding = embedding
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to save resume embedding: {e}")
    finally:
        db.close()


def save_cv_upload_record(user_id: str, file_url: str, storage_path: str, original_filename: Optional[str]) -> str:
    """Insert a new CVUpload row, mark it active, deactivate all previous ones."""
    with SessionLocal() as db:
        db.query(CVUpload).filter(CVUpload.user_id == user_id).update({"is_active": False})
        record = CVUpload(
            id=str(uuid4()),
            user_id=user_id,
            file_url=file_url,
            storage_path=storage_path,
            original_filename=original_filename,
            is_active=True,
            uploaded_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        return record.id


def get_cv_upload_history(user_id: str) -> list:
    with SessionLocal() as db:
        records = (
            db.query(CVUpload)
            .filter(CVUpload.user_id == user_id)
            .order_by(CVUpload.uploaded_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "file_url": r.file_url,
                "storage_path": r.storage_path,
                "original_filename": r.original_filename,
                "is_active": r.is_active,
                "uploaded_at": r.uploaded_at,
            }
            for r in records
        ]


def get_cv_upload_by_id(upload_id: str, user_id: str) -> Optional[dict]:
    with SessionLocal() as db:
        r = db.query(CVUpload).filter(
            CVUpload.id == upload_id,
            CVUpload.user_id == user_id,
        ).first()
        if not r:
            return None
        return {
            "id": r.id,
            "file_url": r.file_url,
            "storage_path": r.storage_path,
            "original_filename": r.original_filename,
            "is_active": r.is_active,
            "uploaded_at": r.uploaded_at,
        }


def set_active_cv_upload(upload_id: str, user_id: str):
    """Deactivate all uploads for the user, then activate the chosen one."""
    with SessionLocal() as db:
        db.query(CVUpload).filter(CVUpload.user_id == user_id).update({"is_active": False})
        db.query(CVUpload).filter(CVUpload.id == upload_id).update({"is_active": True})
        db.commit()