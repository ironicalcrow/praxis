import uuid
from fastapi import HTTPException
from app.core.session import get_session
from app.models import Resume, ResumeSkill, ResumeEducation, ResumeExperience, ResumeProject, ResumeCertification
from app.schemas import ResumeSchema


def save_resume_to_db(parsed_resume: ResumeSchema, user_id: str):
    """Save or update a resume with all related data"""
    db = get_session()
    try:
        existing_resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        
        if existing_resume:
            existing_resume.name = parsed_resume.name
            existing_resume.email = parsed_resume.email
            existing_resume.phone = parsed_resume.phone
            existing_resume.location = parsed_resume.location
            existing_resume.years_of_experience = parsed_resume.years_of_experience
            existing_resume.raw_text = parsed_resume.raw_text
            
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
                user_id=user_id,
                name=parsed_resume.name,
                email=parsed_resume.email,
                phone=parsed_resume.phone,
                location=parsed_resume.location,
                years_of_experience=parsed_resume.years_of_experience,
                raw_text=parsed_resume.raw_text,
            )
            db.add(new_resume)
        
        if parsed_resume.skills:
            for skill in parsed_resume.skills:
                skill_obj = ResumeSkill(
                    id=str(uuid.uuid4()),
                    resume_id=resume_id,
                    skill=skill
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
            "message": "Resume saved successfully"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database save failed: {str(e)}"
        )
    finally:
        db.close()


def fetch_resume_from_db(user_id: str):
    """Fetch a resume with all related data"""
    db = get_session()
    try:
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        
        if not resume:
            raise HTTPException(
                status_code=404,
                detail="No CV found for this user"
            )

        skills = db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume.id).all()
        education = db.query(ResumeEducation).filter(ResumeEducation.resume_id == resume.id).all()
        experience = db.query(ResumeExperience).filter(ResumeExperience.resume_id == resume.id).all()
        projects = db.query(ResumeProject).filter(ResumeProject.resume_id == resume.id).all()
        certifications = db.query(ResumeCertification).filter(ResumeCertification.resume_id == resume.id).all()

        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "name": resume.name,
            "email": resume.email,
            "phone": resume.phone,
            "location": resume.location,
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
            "certifications": [cert.certification for cert in certifications],
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch resume: {str(e)}"
        )
    finally:
        db.close()