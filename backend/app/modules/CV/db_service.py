from fastapi import HTTPException
from app.core.supabase import supabase_admin
from app.schemas import ResumeSchema

def save_resume_to_db(parsed_resume: ResumeSchema, user_id: str):
    try:
        resume_data = {
            "user_id": user_id,
            "name": parsed_resume.name,
            "email": parsed_resume.email,
            "phone": parsed_resume.phone,
            "location": parsed_resume.location,
            "years_of_experience": parsed_resume.years_of_experience,
            "raw_text": parsed_resume.raw_text,
        }

        existing_resume = (
            supabase_admin
            .table("resumes")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )

        if existing_resume.data:
            resume_id = existing_resume.data[0]["id"]

            (
                supabase_admin
                .table("resumes")
                .update(resume_data)
                .eq("id", resume_id)
                .execute()
            )

            clear_old_resume_children(resume_id)

        else:
            response = (
                supabase_admin
                .table("resumes")
                .insert(resume_data)
                .execute()
            )

            if not response.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save resume"
                )

            resume_id = response.data[0]["id"]

        insert_resume_children(parsed_resume, resume_id)

        return {
            "resume_id": resume_id,
            "message": "Resume saved successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database save failed: {str(e)}"
        )


def clear_old_resume_children(resume_id: str):
    child_tables = [
        "resume_skills",
        "resume_education",
        "resume_experience",
        "resume_projects",
        "resume_certifications",
    ]

    for table in child_tables:
        (
            supabase_admin
            .table(table)
            .delete()
            .eq("resume_id", resume_id)
            .execute()
        )


def insert_resume_children(parsed_resume: ResumeSchema, resume_id: str):
    if parsed_resume.skills:
        skills_data = [
            {
                "resume_id": resume_id,
                "skill": skill
            }
            for skill in parsed_resume.skills
        ]

        (
            supabase_admin
            .table("resume_skills")
            .insert(skills_data)
            .execute()
        )

    if parsed_resume.education:
        education_data = [
            {
                "resume_id": resume_id,
                "degree": edu.degree,
                "institution": edu.institution,
                "year": edu.year,
                "gpa": edu.gpa,
            }
            for edu in parsed_resume.education
        ]

        (
            supabase_admin
            .table("resume_education")
            .insert(education_data)
            .execute()
        )

    if parsed_resume.experience:
        experience_data = [
            {
                "resume_id": resume_id,
                "role": exp.role,
                "organization": exp.organization,
                "description": exp.description,
            }
            for exp in parsed_resume.experience
        ]

        (
            supabase_admin
            .table("resume_experience")
            .insert(experience_data)
            .execute()
        )

    if parsed_resume.projects:
        projects_data = [
            {
                "resume_id": resume_id,
                "name": project.name,
                "description": project.description,
                "technology": project.technology,
            }
            for project in parsed_resume.projects
        ]

        (
            supabase_admin
            .table("resume_projects")
            .insert(projects_data)
            .execute()
        )

    if parsed_resume.certifications:
        certifications_data = [
            {
                "resume_id": resume_id,
                "certification": certification,
            }
            for certification in parsed_resume.certifications
        ]

        (
            supabase_admin
            .table("resume_certifications")
            .insert(certifications_data)
            .execute()
        )


def fetch_resume_from_db(user_id: str):
    try:
        resume_response = (
            supabase_admin
            .table("resumes")
            .select("*")
            .eq("user_id", user_id)
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

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch resume: {str(e)}"
        )