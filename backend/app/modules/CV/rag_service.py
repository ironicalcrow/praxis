"""
CV Section RAG Service

Embeds individual CV section rows (skills, experience, projects, education,
certifications) so they can be semantically retrieved at chat time.

Two public async functions:
  embed_resume_sections(resume_id)  — called after CV upload (background)
  retrieve_cv_evidence(db, user_id, query) — called before each LLM call
"""

import asyncio

from sqlalchemy.orm import Session

from app.core.llm_caller import embed_text
from app.modules.CV.models import (
    Resume,
    ResumeSkill,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeCertification,
)


# ── Text converters ────────────────────────────────────────────────────────────

def skills_to_text(skills: list) -> str:
    names = [s.skill for s in skills if s.skill]
    return "Skills: " + ", ".join(names) if names else ""


def experience_to_text(exp) -> str:
    role = exp.role or ""
    org = exp.organization or ""
    desc = (exp.description or "")[:300]
    return f"{role} at {org}: {desc}".strip(" :")


def project_to_text(proj) -> str:
    name = proj.name or ""
    tech = proj.technology or ""
    desc = (proj.description or "")[:300]
    parts = [name]
    if tech:
        parts.append(f"({tech})")
    if desc:
        parts.append(f": {desc}")
    return " ".join(parts)


def education_to_text(edu) -> str:
    degree = edu.degree or ""
    inst = edu.institution or ""
    year = edu.year or ""
    gpa = edu.gpa or ""
    text = f"{degree} from {inst}"
    if year:
        text += f" ({year})"
    if gpa:
        text += f", GPA: {gpa}"
    return text.strip()


def certification_to_text(cert) -> str:
    return cert.certification or ""


# ── Section embedding (called after CV upload) ─────────────────────────────────

async def embed_resume_sections(resume_id: str) -> None:
    """
    Embed each CV section row and save the vectors back to DB.
    Opens its own session — safe to call from background tasks.
    All failures are logged and swallowed so they never block CV upload.
    """
    from app.core.session import SessionLocal

    def _load_sections():
        with SessionLocal() as db:
            skills = db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume_id).all()
            experiences = db.query(ResumeExperience).filter(ResumeExperience.resume_id == resume_id).all()
            projects = db.query(ResumeProject).filter(ResumeProject.resume_id == resume_id).all()
            educations = db.query(ResumeEducation).filter(ResumeEducation.resume_id == resume_id).all()
            certifications = db.query(ResumeCertification).filter(ResumeCertification.resume_id == resume_id).all()
            return (
                [(s.id, s.skill) for s in skills],
                [(e.id, experience_to_text(e)) for e in experiences],
                [(p.id, project_to_text(p)) for p in projects],
                [(ed.id, education_to_text(ed)) for ed in educations],
                [(c.id, certification_to_text(c)) for c in certifications],
            )

    try:
        skill_rows, exp_rows, proj_rows, edu_rows, cert_rows = await asyncio.to_thread(_load_sections)
    except Exception as e:
        print(f"[RAG] ⚠️ Failed to load CV sections for embedding: {e}")
        return

    updates: list[tuple] = []  # (model_class, row_id, vector)

    # Skills: one grouped embedding shared across all skill rows
    if skill_rows:
        try:
            skill_text = "Skills: " + ", ".join(name for _, name in skill_rows if name)
            if skill_text.strip():
                skill_vec = await embed_text(skill_text)
                for row_id, _ in skill_rows:
                    updates.append((ResumeSkill, row_id, skill_vec))
        except Exception as e:
            print(f"[RAG] ⚠️ Skill embedding failed: {e}")

    # Experience, projects, education, certifications: one embedding per row
    for section_rows, model_class, label in [
        (exp_rows, ResumeExperience, "experience"),
        (proj_rows, ResumeProject, "project"),
        (edu_rows, ResumeEducation, "education"),
        (cert_rows, ResumeCertification, "certification"),
    ]:
        for row_id, text in section_rows:
            if not text or not text.strip():
                continue
            try:
                vec = await embed_text(text)
                updates.append((model_class, row_id, vec))
            except Exception as e:
                print(f"[RAG] ⚠️ {label} embedding failed for {row_id}: {e}")

    if not updates:
        return

    def _save(updates):
        with SessionLocal() as db:
            for model_class, row_id, vector in updates:
                obj = db.query(model_class).filter(model_class.id == row_id).first()
                if obj:
                    obj.embedding = vector
            db.commit()

    try:
        await asyncio.to_thread(_save, updates)
        print(f"[RAG] ✅ Saved {len(updates)} section embeddings for resume {resume_id}.")
    except Exception as e:
        print(f"[RAG] ⚠️ Failed to save section embeddings: {e}")


# ── CV evidence retrieval (called before each LLM turn) ───────────────────────

async def retrieve_cv_evidence(
    db: Session,
    user_id: str,
    query: str,
    limit_per_section: int = 3,
) -> str:
    """
    Embed the query, then cosine-search each CV section table.
    Returns a formatted evidence string ready to inject into the system prompt.
    Returns "" if no embeddings exist yet (graceful fallback to structured summary).
    """
    def _get_resume_id():
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        return resume.id if resume else None

    resume_id = await asyncio.to_thread(_get_resume_id)
    if not resume_id:
        return ""

    try:
        query_vec = await embed_text(query)
    except Exception as e:
        print(f"[RAG] ⚠️ Query embedding failed: {e}")
        return ""

    evidence_blocks: list[str] = []

    def _query_skills():
        return (
            db.query(ResumeSkill)
            .filter(ResumeSkill.resume_id == resume_id, ResumeSkill.embedding.is_not(None))
            .order_by(ResumeSkill.embedding.cosine_distance(query_vec))
            .limit(1)  # skills are one block; one row carries the full grouped embedding
            .all()
        )

    def _query_section(model_class, resume_id, limit):
        return (
            db.query(model_class)
            .filter(
                model_class.resume_id == resume_id,
                model_class.embedding.is_not(None),
            )
            .order_by(model_class.embedding.cosine_distance(query_vec))
            .limit(limit)
            .all()
        )

    try:
        # Skills — return all skill names if any row matches
        skill_rows = await asyncio.to_thread(_query_skills)
        if skill_rows:
            all_skills = await asyncio.to_thread(
                lambda: db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume_id).all()
            )
            names = [s.skill for s in all_skills if s.skill]
            if names:
                evidence_blocks.append("[SKILLS]\n" + ", ".join(names))

        # Experience
        exp_rows = await asyncio.to_thread(_query_section, ResumeExperience, resume_id, limit_per_section)
        for exp in exp_rows:
            text = experience_to_text(exp)
            if text:
                evidence_blocks.append(f"[EXPERIENCE]\n{text}")

        # Projects
        proj_rows = await asyncio.to_thread(_query_section, ResumeProject, resume_id, limit_per_section)
        for proj in proj_rows:
            text = project_to_text(proj)
            if text:
                evidence_blocks.append(f"[PROJECT]\n{text}")

        # Education
        edu_rows = await asyncio.to_thread(_query_section, ResumeEducation, resume_id, 2)
        for edu in edu_rows:
            text = education_to_text(edu)
            if text:
                evidence_blocks.append(f"[EDUCATION]\n{text}")

        # Certifications
        cert_rows = await asyncio.to_thread(_query_section, ResumeCertification, resume_id, 2)
        for cert in cert_rows:
            text = certification_to_text(cert)
            if text:
                evidence_blocks.append(f"[CERTIFICATION]\n{text}")

    except Exception as e:
        print(f"[RAG] ⚠️ Evidence retrieval failed: {e}")
        return ""

    return "\n\n".join(evidence_blocks)
