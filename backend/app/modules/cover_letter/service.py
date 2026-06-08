from sqlalchemy.orm import Session

from app.core.chatbot_caller import call_chatbot
from app.modules.cover_letter.models import CoverLetter
from app.modules.cover_letter import db_service as cl_db


TONE_INSTRUCTIONS = {
    "professional": "formal, polished, and confident",
    "enthusiastic": "warm, energetic, and passionate about the role",
    "concise": "brief and direct — no more than 250 words",
}


async def generate_cover_letter(
    user_id: str,
    job_id: str,
    tone: str = "professional",
    db: Session = None,
) -> CoverLetter:
    """
    Generate a tailored cover letter using the user's CV and the job description,
    then save and return the draft.
    """
    from app.modules.CV.db_service import fetch_resume_from_db
    from app.modules.jobs.models import Job

    resume = fetch_resume_from_db(user_id)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    tone_desc = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])

    cv_block = (
        f"Name: {resume.get('name', '')}\n"
        f"Skills: {', '.join(resume.get('skills', []))}\n"
        f"Experience:\n" +
        "\n".join(
            f"  {e.get('role', '')} at {e.get('organization', '')}: {(e.get('description') or '')[:200]}"
            for e in (resume.get("experience") or [])
        ) +
        f"\nEducation:\n" +
        "\n".join(
            f"  {e.get('degree', '')} from {e.get('institution', '')}"
            for e in (resume.get("education") or [])
        )
    )

    job_block = (
        f"Title: {job.title}\n"
        f"Company: {job.company_name}\n"
        f"Location: {job.location or 'Remote'}\n"
        f"Required skills: {', '.join(job.skills_and_technologies or [])}\n"
        f"Description: {(job.description or '')[:600]}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                f"You are an expert career coach writing cover letters. "
                f"Write a {tone_desc} cover letter tailored specifically to the job. "
                f"Ground every paragraph in the candidate's actual experience. "
                f"Do not use filler phrases. Output only the letter text — no subject line, no metadata."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a cover letter for this candidate applying to this job.\n\n"
                f"=== CANDIDATE CV ===\n{cv_block}\n\n"
                f"=== JOB ===\n{job_block}"
            ),
        },
    ]

    content = await call_chatbot(messages=messages, temperature=0.7)
    return cl_db.save_cover_letter(db, user_id=user_id, job_id=job_id, content=content, tone=tone)
