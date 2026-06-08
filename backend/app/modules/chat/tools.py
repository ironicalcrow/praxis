"""
Tool executor for the AI assistant's function-calling capability.

Read tools execute immediately. Write tools are only called after the user
has explicitly confirmed via the request_confirmation pseudo-tool.
All executors return ToolExecutionResult — never plain strings.
"""

import asyncio
from sqlalchemy.orm import Session

from app.modules.chat.types import ToolExecutionResult


# ── Tool schema definitions (sent to LLM) ─────────────────────────────────────

GENERAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search for live job listings matching a query. Execute immediately — no confirmation needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Job title or keywords"},
                    "location": {"type": "string", "description": "City or country. Empty string for remote."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_applications",
            "description": "Get the user's job applications grouped by status. Execute immediately.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_goals",
            "description": "Get the user's active career goals. Execute immediately.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_roadmaps",
            "description": "Get the user's career roadmaps. Execute immediately.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_roadmap",
            "description": "Generate and save a career roadmap. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["conversation", "job"],
                        "description": "'conversation' to generate from chat history, 'job' to generate from a specific job.",
                    },
                    "job_id": {"type": "string", "description": "Required if source is 'job'."},
                },
                "required": ["source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goals",
            "description": "Create trackable goals from a roadmap's milestones. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "roadmap_id": {"type": "string"},
                    "milestone_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Milestone IDs to promote to goals.",
                    },
                },
                "required": ["roadmap_id", "milestone_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_confirmation",
            "description": (
                "Call this BEFORE any write tool. Provide action_description (human-readable summary), "
                "pending_tool (exact name of the write tool you will call after confirmation), "
                "and pending_args (its arguments as a JSON object)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_description": {
                        "type": "string",
                        "description": "Clear, user-readable description of the action that will be taken.",
                    },
                    "pending_tool": {
                        "type": "string",
                        "enum": [
                            "generate_roadmap", "create_goals", "save_to_tracker",
                            "draft_cover_letter", "update_application_status", "add_application_note",
                        ],
                        "description": "The write tool you will call once the user confirms.",
                    },
                    "pending_args": {
                        "type": "object",
                        "description": "Arguments you will pass to pending_tool.",
                    },
                },
                "required": ["action_description", "pending_tool"],
            },
        },
    },
]

JOB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_fit_score",
            "description": "Get the user's fit score and skill gap analysis for the selected job. Execute immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_tracker",
            "description": "Save the selected job to the user's application tracker with status 'saved'. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_cover_letter",
            "description": "Generate and save a tailored cover letter for the selected job. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "tone": {
                        "type": "string",
                        "enum": ["professional", "enthusiastic", "concise"],
                        "description": "Writing tone for the cover letter.",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_application_status",
            "description": "Update the status of a job application. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string"},
                    "new_status": {
                        "type": "string",
                        "enum": ["saved", "applied", "interviewing", "offer", "rejected"],
                    },
                    "reason": {"type": "string", "description": "Optional reason for the status change."},
                },
                "required": ["application_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_application_note",
            "description": "Add a note to a job application. WRITE TOOL — call request_confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string"},
                    "content": {"type": "string", "description": "The note content."},
                },
                "required": ["application_id", "content"],
            },
        },
    },
]


def get_tools_for_context(context_type: str) -> list:
    if context_type == "job":
        return GENERAL_TOOLS + JOB_TOOLS
    return GENERAL_TOOLS


# ── Tool executor dispatcher ───────────────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    tool_args: dict,
    user_id: str,
    conversation_id: str,
    db: Session,
) -> ToolExecutionResult:
    try:
        if tool_name == "request_confirmation":
            return await _request_confirmation(tool_args)
        elif tool_name == "search_jobs":
            return await _search_jobs(tool_args, user_id, db)
        elif tool_name == "get_fit_score":
            return await _get_fit_score(tool_args, user_id, db)
        elif tool_name == "get_my_applications":
            return await _get_my_applications(user_id)
        elif tool_name == "get_my_goals":
            return _get_my_goals(user_id, db)
        elif tool_name == "get_my_roadmaps":
            return _get_my_roadmaps(user_id, db)
        elif tool_name == "save_to_tracker":
            return await _save_to_tracker(tool_args, user_id, db)
        elif tool_name == "draft_cover_letter":
            return await _draft_cover_letter(tool_args, user_id, db)
        elif tool_name == "generate_roadmap":
            return await _generate_roadmap(tool_args, user_id, conversation_id, db)
        elif tool_name == "create_goals":
            return await _create_goals(tool_args, user_id, db)
        elif tool_name == "update_application_status":
            return await _update_application_status(tool_args, user_id)
        elif tool_name == "add_application_note":
            return await _add_application_note(tool_args, user_id)
        else:
            return ToolExecutionResult(
                status="unsupported",
                message="I can't do that directly from the chat. Please use the relevant section of the app.",
            )
    except Exception as e:
        print(f"[Chat] Tool error ({tool_name}): {e}")
        return ToolExecutionResult(status="failed", message="Something went wrong while processing that request. Please try again.")


# ── Pseudo-tool: confirmation gate ────────────────────────────────────────────

async def _request_confirmation(args: dict) -> ToolExecutionResult:
    desc = args.get("action_description", "this action")
    return ToolExecutionResult(status="confirmation_required", message=desc)


# ── Read tools ─────────────────────────────────────────────────────────────────

async def _search_jobs(args: dict, user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.jobs.controller import search_live_jobs, get_job_detail
    from app.modules.CV.db_service import fetch_resume_from_db
    query = args.get("query", "")
    location = args.get("location", "")
    try:
        resume = fetch_resume_from_db(user_id)
        resume_id = str(resume.get("id", ""))
        jobs = await search_live_jobs(
            query=query, user_id=user_id, resume_id=resume_id,
            location=location, page=1, num_pages=1,
        )
        if not jobs:
            return ToolExecutionResult(
                status="handled",
                message=f"No jobs found for '{query}' in '{location or 'any location'}'.",
                payload_type="job_search_results",
                payload={"jobs": []},
            )

        # Persist any live/temp jobs to DB in the background so follow-up tool calls
        # (save_to_tracker, draft_cover_letter, etc.) can find them by ID.
        async def _bg_persist(jid: str):
            try:
                await get_job_detail(jid, current_user=None)
            except Exception:
                pass

        for job in jobs:
            if job.id:
                asyncio.create_task(_bg_persist(str(job.id)))

        lines = [f"Found {len(jobs)} jobs for '{query}':"]
        for j in jobs[:5]:
            score = ""
            if hasattr(j, "fit_score") and j.fit_score:
                score = f" — {j.fit_score.fit_score:.0f}% match"
            lines.append(f"• {j.title} @ {j.company_name} ({j.location or 'Remote'}){score} [ID: {j.id}]")
        return ToolExecutionResult(
            status="handled",
            message="\n".join(lines),
            payload_type="job_search_results",
            payload={"jobs": [j.model_dump() for j in jobs[:10]]},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message="Something went wrong while searching for jobs. Please try again.")


async def _get_fit_score(args: dict, user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.jobs.models import Job
    from app.modules.jobs.services.fit_scorer import compute_fit_score
    from app.modules.jobs.services.job_suggestion import _job_to_profile
    from app.modules.CV.db_service import fetch_resume_from_db
    from app.modules.CV.schemas import ResumeSchema
    job_id = args.get("job_id", "")
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return ToolExecutionResult(status="failed", message=f"Job {job_id} not found.")
        resume_data = fetch_resume_from_db(user_id)
        candidate = ResumeSchema(**resume_data)
        profile = _job_to_profile(job)
        fit = await compute_fit_score(profile=profile, candidate=candidate, add_reasoning=True)
        strengths_preview = ", ".join(fit.strengths[:4]) or "none identified"
        weaknesses_preview = ", ".join(fit.weaknesses[:4]) or "none identified"
        return ToolExecutionResult(
            status="handled",
            message=(
                f"Fit score: {fit.fit_score:.0f}% — {fit.verdict}\n"
                f"Matched: {strengths_preview}\n"
                f"Missing: {weaknesses_preview}"
            ),
            payload_type="fit_score",
            payload=fit.model_dump(),
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Fit score failed: {e}")


async def _get_my_applications(user_id: str) -> ToolExecutionResult:
    from app.modules.application.db_service import fetch_kanban_applications_from_db
    try:
        kanban = fetch_kanban_applications_from_db(user_id)
        total = sum(len(v) for v in kanban.values())
        summary = ", ".join(
            f"{len(kanban[k])} {k}" for k in kanban if kanban[k]
        ) or "no applications yet"
        return ToolExecutionResult(
            status="handled",
            message=f"You have {total} application(s): {summary}.",
            payload_type="application_kanban",
            payload=kanban,
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Could not fetch applications: {e}")


def _get_my_goals(user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.goals.models import Goal
    try:
        goals = (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.status != "completed")
            .order_by(Goal.target_date.asc().nullslast())
            .limit(20)
            .all()
        )
        if not goals:
            return ToolExecutionResult(
                status="handled",
                message="You have no active goals yet.",
                payload_type="goals",
                payload={"goals": []},
            )
        goal_list = [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "status": g.status,
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "source_type": g.source_type,
            }
            for g in goals
        ]
        lines = [f"• [{g['status']}] {g['title']}" for g in goal_list[:5]]
        return ToolExecutionResult(
            status="handled",
            message=f"You have {len(goals)} active goal(s):\n" + "\n".join(lines),
            payload_type="goals",
            payload={"goals": goal_list},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Could not fetch goals: {e}")


def _get_my_roadmaps(user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.roadmap.models import Roadmap, RoadmapPhase, RoadmapMilestone
    try:
        roadmaps = (
            db.query(Roadmap)
            .filter(Roadmap.user_id == user_id)
            .order_by(Roadmap.created_at.desc())
            .limit(10)
            .all()
        )
        if not roadmaps:
            return ToolExecutionResult(
                status="handled",
                message="You have no roadmaps yet.",
                payload_type="roadmaps",
                payload={"roadmaps": []},
            )
        roadmap_list = []
        for r in roadmaps:
            phases = db.query(RoadmapPhase).filter(RoadmapPhase.roadmap_id == r.id).all()
            milestone_count = sum(
                db.query(RoadmapMilestone).filter(RoadmapMilestone.phase_id == p.id).count()
                for p in phases
            )
            roadmap_list.append({
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "source_type": r.source_type,
                "phase_count": len(phases),
                "milestone_count": milestone_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return ToolExecutionResult(
            status="handled",
            message=f"You have {len(roadmaps)} roadmap(s).",
            payload_type="roadmaps",
            payload={"roadmaps": roadmap_list},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Could not fetch roadmaps: {e}")


# ── Write tools ────────────────────────────────────────────────────────────────

async def _save_to_tracker(args: dict, user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.jobs.models import Job
    from app.modules.application.models import ApplicationStatus
    from app.modules.application.db_service import (
        create_application_to_db,
        serialize_application_from_db,
    )
    job_id = args.get("job_id", "")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return ToolExecutionResult(status="failed", message=f"Job {job_id} not found in database. Open the job detail first.")
    try:
        apply_url = None
        if job.apply_urls:
            apply_url = job.apply_urls[0] if isinstance(job.apply_urls, list) else str(job.apply_urls)
        application = create_application_to_db(
            db=db,
            user_id=user_id,
            job_title=job.title,
            company=job.company_name,
            job_id=job.id,
            location=job.location,
            apply_url=apply_url,
            source="chat",
            salary=job.salary,
            status=ApplicationStatus.SAVED,
        )
        db.commit()
        payload = serialize_application_from_db(db, application)
        return ToolExecutionResult(
            status="handled",
            message=f"Saved '{job.title}' at {job.company_name} to your tracker.",
            payload_type="application",
            payload=payload,
            should_notify=True,
            notification_type="job_saved",
            notification_title="Job saved to tracker",
            notification_message=f"'{job.title}' at {job.company_name} has been added to your tracker.",
            notification_data={"application_id": payload["id"], "job_id": job_id},
        )
    except Exception as e:
        db.rollback()
        return ToolExecutionResult(status="failed", message=f"Could not save to tracker: {e}")


async def _draft_cover_letter(args: dict, user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.cover_letter.service import generate_cover_letter
    job_id = args.get("job_id", "")
    tone = args.get("tone", "professional")
    try:
        draft = await generate_cover_letter(user_id=user_id, job_id=job_id, tone=tone, db=db)
        return ToolExecutionResult(
            status="handled",
            message=f"Cover letter drafted and saved (ID: {draft.id}).",
            payload_type="cover_letter",
            payload={
                "id": draft.id,
                "job_id": job_id,
                "content": draft.content,
                "tone": tone,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
            },
            should_notify=True,
            notification_type="cover_letter_generated",
            notification_title="Cover letter ready",
            notification_message=f"Your cover letter has been drafted and saved.",
            notification_data={"cover_letter_id": draft.id, "job_id": job_id},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Cover letter generation failed: {e}")


async def _generate_roadmap(args: dict, user_id: str, conversation_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.roadmap.service import generate_from_conversation, generate_from_job
    from app.modules.roadmap.models import RoadmapPhase, RoadmapMilestone
    source = args.get("source", "conversation")
    job_id = args.get("job_id")
    try:
        if source == "job" and job_id:
            roadmap = await generate_from_job(job_id=job_id, user_id=user_id, db=db)
        else:
            roadmap = await generate_from_conversation(conversation_id=conversation_id, user_id=user_id, db=db)
        phases = db.query(RoadmapPhase).filter(RoadmapPhase.roadmap_id == roadmap.id).all()
        phases_data = []
        total_milestones = 0
        for p in phases:
            milestones = db.query(RoadmapMilestone).filter(RoadmapMilestone.phase_id == p.id).all()
            total_milestones += len(milestones)
            phases_data.append({
                "id": p.id,
                "title": p.title,
                "order_index": p.order_index,
                "duration_weeks": p.duration_weeks,
                "milestones": [
                    {"id": m.id, "title": m.title, "description": m.description,
                     "estimated_days": m.estimated_days}
                    for m in milestones
                ],
            })
        return ToolExecutionResult(
            status="handled",
            message=(
                f"Roadmap '{roadmap.title}' created with {len(phases)} phase(s) and "
                f"{total_milestones} milestone(s). Roadmap ID: {roadmap.id}."
            ),
            payload_type="roadmap",
            payload={"id": roadmap.id, "title": roadmap.title, "description": roadmap.description, "phases": phases_data},
            should_notify=True,
            notification_type="roadmap_generated",
            notification_title="Career roadmap ready",
            notification_message=f"Your roadmap '{roadmap.title}' has been created.",
            notification_data={"roadmap_id": roadmap.id},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Roadmap generation failed: {e}")


async def _create_goals(args: dict, user_id: str, db: Session) -> ToolExecutionResult:
    from app.modules.goals.db_service import create_goals_from_milestones
    roadmap_id = args.get("roadmap_id", "")
    milestone_ids = args.get("milestone_ids", [])
    try:
        goals = create_goals_from_milestones(db, user_id=user_id, roadmap_id=roadmap_id, milestone_ids=milestone_ids)
        goal_list = [
            {"id": g.id, "title": g.title, "status": g.status,
             "target_date": g.target_date.isoformat() if g.target_date else None}
            for g in goals
        ]
        return ToolExecutionResult(
            status="handled",
            message=f"Created {len(goals)} goal(s) from the roadmap milestones.",
            payload_type="goals",
            payload={"goals": goal_list},
            should_notify=True,
            notification_type="goals_created",
            notification_title="Goals created",
            notification_message=f"{len(goals)} roadmap milestone(s) added to your goals.",
            notification_data={"count": len(goals), "roadmap_id": roadmap_id},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Goal creation failed: {e}")


async def _update_application_status(args: dict, user_id: str) -> ToolExecutionResult:
    from app.modules.application.db_service import update_application_status_db
    application_id = args.get("application_id", "")
    new_status = args.get("new_status", "")
    reason = args.get("reason")
    try:
        result = update_application_status_db(
            user_id=user_id,
            application_id=application_id,
            new_status=new_status,
            reason=reason,
        )
        return ToolExecutionResult(
            status="handled",
            message=f"Application status updated to '{new_status}'.",
            payload_type="application_status",
            payload=result,
            should_notify=True,
            notification_type="application_status_changed",
            notification_title="Application status updated",
            notification_message=f"Application status changed to '{new_status}'.",
            notification_data={"application_id": application_id, "new_status": new_status},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Status update failed: {e}")


async def _add_application_note(args: dict, user_id: str) -> ToolExecutionResult:
    from app.modules.application.db_service import add_application_note_db
    application_id = args.get("application_id", "")
    content = args.get("content", "")
    try:
        result = add_application_note_db(
            user_id=user_id,
            application_id=application_id,
            content=content,
        )
        return ToolExecutionResult(
            status="handled",
            message="Note added to application.",
            payload_type="application_note",
            payload=result,
            should_notify=True,
            notification_type="application_note_added",
            notification_title="Note added",
            notification_message="A note has been added to your application.",
            notification_data={"application_id": application_id, "note_id": result.get("note_id")},
        )
    except Exception as e:
        return ToolExecutionResult(status="failed", message=f"Note creation failed: {e}")
