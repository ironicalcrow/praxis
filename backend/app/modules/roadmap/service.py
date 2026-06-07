import json
import re

from sqlalchemy.orm import Session

from app.core.chatbot_caller import call_chatbot as call_llm
from app.modules.chat import db_service as chat_db
from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.roadmap import db_service as roadmap_db
from app.modules.roadmap.models import Roadmap


# ── LLM Output Parser ──────────────────────────────────────────────────────────

def _parse_roadmap_json(raw: str) -> dict:
    """
    Safely extract and parse a JSON object from raw LLM output.
    Strips markdown code fences if present.
    """
    raw = raw.strip()
    # Strip ```json ... ``` wrappers
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
    # Find first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM roadmap response")
    return json.loads(match.group(0))


# ── Roadmap LLM Prompt Template ────────────────────────────────────────────────

_ROADMAP_JSON_SCHEMA = (
    '{"title": "...", "description": "...", "phases": ['
    '{"title": "...", "description": "...", "duration_weeks": 4, "order_index": 1, '
    '"milestones": ['
    '{"title": "Learn/Build <specific skill or deliverable>", '
    '"description": "Skill: <exact skill/technology>. Practice: <concrete exercise or mini-project to build>. Outcome: <what you can do after>.", '
    '"resource_url": null, "order_index": 1}'
    "]}"
    "]}"
)

_ROADMAP_SYSTEM = (
    "You are a career development expert. Generate a structured, skill-oriented career roadmap in JSON. "
    "RULES FOR MILESTONES — every milestone must: "
    "(1) target ONE specific, named skill or technology (e.g. 'React hooks', 'SQL window functions', 'Docker multi-stage builds'); "
    "(2) include a concrete hands-on practice exercise or mini-project the learner will build; "
    "(3) state a clear outcome — what the learner can do or demonstrate after completing it. "
    "Milestones must be practical and verifiable, not vague (BAD: 'Improve Python skills'; GOOD: 'Build a CLI task manager using Click and pytest'). "
    "Return ONLY valid JSON — no markdown, no explanation. "
    f"Schema:\n{_ROADMAP_JSON_SCHEMA}"
)


# ── Generate from Conversation ─────────────────────────────────────────────────

async def generate_from_conversation(
    conversation_id: str, user_id: str, db: Session
) -> Roadmap:
    """
    Reads the conversation transcript + summary, sends to LLM,
    receives a structured roadmap (phases + milestones), persists and returns it.
    """
    conv = chat_db.get_conversation(db, conversation_id, user_id)
    if not conv:
        raise ValueError("Conversation not found")

    all_messages = chat_db.get_conversation_all_messages(db, conversation_id)
    transcript_lines = []
    for msg in all_messages[-50:]:
        prefix = "User" if msg.role == "user" else "Coach"
        transcript_lines.append(f"{prefix}: {msg.content[:600]}")
    transcript = "\n".join(transcript_lines)

    summary_block = f"\nConversation Summary: {conv.summary}" if conv.summary else ""

    prompt_messages = [
        {"role": "system", "content": _ROADMAP_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Generate a career roadmap based on this coaching conversation."
                f"{summary_block}\n\n"
                f"Conversation transcript:\n{transcript}\n\n"
                "Create 3-5 phases with 2-4 milestones each. "
                "Each milestone is a standalone goal the user will work toward — make it skill-specific and include a hands-on exercise. "
                "Base skills on the actual topics and goals discussed in the conversation."
            ),
        },
    ]

    raw = await call_llm(messages=prompt_messages, temperature=0.4, json_mode=True)
    data = _parse_roadmap_json(raw)

    return roadmap_db.create_roadmap(
        db=db,
        user_id=user_id,
        title=data.get("title", f"Career Roadmap from: {conv.title}"),
        description=data.get("description"),
        source_type="chat",
        source_id=conversation_id,
        phases_data=data.get("phases", []),
    )


# ── Generate from Job (Gap Analysis) ──────────────────────────────────────────

async def generate_from_job(
    job_id: str, user_id: str, db: Session
) -> Roadmap:
    """
    Compares the user's CV skills against the job's requirements,
    generates a targeted upskilling roadmap to close the gap.
    """
    from app.modules.jobs.models import Job

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError("Job not found")

    try:
        resume = fetch_resume_from_db(user_id)
    except Exception:
        resume = {}

    user_skills = set(s.lower() for s in (resume.get("skills") or []))
    job_skills = job.skills_and_technologies or []
    job_qualifications = job.qualifications or []

    missing_skills = [s for s in job_skills if s.lower() not in user_skills]
    matched_skills = [s for s in job_skills if s.lower() in user_skills]

    prompt_messages = [
        {"role": "system", "content": _ROADMAP_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Job Title: {job.title} at {job.company_name}\n"
                f"Job Description: {(job.description or '')[:800]}\n"
                f"Required Skills: {', '.join(job_skills)}\n"
                f"Required Qualifications: {', '.join(job_qualifications)}\n\n"
                f"User's Current Skills: {', '.join(resume.get('skills') or [])}\n"
                f"Already Matched Skills: {', '.join(matched_skills)}\n"
                f"Skills Gap (MISSING): {', '.join(missing_skills)}\n\n"
                "Generate a focused upskilling roadmap to bridge the skill gap for this role. "
                "3-5 phases, 2-4 milestones each. Each milestone is a standalone skill goal — "
                "name the exact skill/tool, give a concrete practice exercise, and state a verifiable outcome. "
                "Include concrete resource suggestions where relevant."
            ),
        },
    ]

    raw = await call_llm(messages=prompt_messages, temperature=0.4, json_mode=True)
    data = _parse_roadmap_json(raw)

    return roadmap_db.create_roadmap(
        db=db,
        user_id=user_id,
        title=data.get("title", f"Path to: {job.title} at {job.company_name}"),
        description=data.get("description"),
        source_type="job",
        source_id=job_id,
        phases_data=data.get("phases", []),
    )


# ── Insight Preview Builder ────────────────────────────────────────────────────

def build_roadmap_insight_preview(roadmap: Roadmap) -> dict:
    """
    After roadmap generation, return the full roadmap alongside a flat list of
    suggested goals (one per milestone). The user reviews this and confirms
    which milestones to promote to actual goals via POST /goals/from-roadmap/{id}.
    """
    suggested_goals = []
    for phase in roadmap.phases:
        for milestone in phase.milestones:
            suggested_goals.append({
                "title": milestone.title,
                "description": milestone.description,
                "milestone_id": milestone.id,
                "phase_title": phase.title,
            })

    return {
        "roadmap": roadmap,
        "suggested_goals": suggested_goals,
    }
