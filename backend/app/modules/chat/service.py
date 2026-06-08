import asyncio
import json

import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from app.core.chatbot_caller import call_chatbot as call_llm, ChatbotCallerError
from app.core.config import settings
from app.modules.chat import db_service as chat_db
from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.chat.types import ToolExecutionResult

SESSION_ROTATION_THRESHOLD = 15

_CONFIRM_TOKENS = {
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "go ahead",
    "proceed", "confirm", "do it", "sounds good", "alright", "absolutely",
    "please", "please do", "go", "fine", "agreed",
}
_CANCEL_TOKENS = {
    "no", "nope", "cancel", "abort", "stop", "never mind",
    "nevermind", "don't", "dont", "skip",
}


def _is_confirmation(text: str) -> bool:
    t = text.strip().lower()
    return any(tok in t for tok in _CONFIRM_TOKENS) and not any(tok in t for tok in _CANCEL_TOKENS)


def _is_cancellation(text: str) -> bool:
    return any(tok in text.strip().lower() for tok in _CANCEL_TOKENS)


async def _clear_pending(session_id: str) -> None:
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        await r.delete(f"pending_tool:{session_id}")
    except Exception:
        pass
    finally:
        await r.aclose()


# ── CV RAG Context ─────────────────────────────────────────────────────────────

def build_cv_context(user_id: str, db: Session) -> str:
    """
    Fetch the user's parsed resume from DB and format it as a
    concise, structured context block for RAG injection.
    """
    try:
        resume = fetch_resume_from_db(user_id)
    except Exception:
        return "No CV uploaded yet. Advise the user to upload their CV first."

    lines = [f"**Name:** {resume.get('name', 'N/A')}"]

    if resume.get("location"):
        lines.append(f"**Location:** {resume['location']}")

    if resume.get("years_of_experience"):
        lines.append(f"**Years of Experience:** {resume['years_of_experience']}")

    if resume.get("skills"):
        lines.append(f"**Skills:** {', '.join(resume['skills'])}")

    if resume.get("experience"):
        exp_lines = []
        for exp in resume["experience"]:
            role = exp.get("role", "")
            org = exp.get("organization", "")
            desc = (exp.get("description") or "")[:200]
            exp_lines.append(f"  - {role} at {org}: {desc}")
        lines.append("**Work Experience:**\n" + "\n".join(exp_lines))

    if resume.get("education"):
        edu_lines = [
            f"  - {e.get('degree', '')} from {e.get('institution', '')} ({e.get('year', '')})"
            for e in resume["education"]
        ]
        lines.append("**Education:**\n" + "\n".join(edu_lines))

    if resume.get("projects"):
        proj_lines = [
            f"  - {p.get('name', '')}: {(p.get('description') or '')[:150]}"
            for p in resume["projects"]
        ]
        lines.append("**Projects:**\n" + "\n".join(proj_lines))

    if resume.get("certifications"):
        lines.append(f"**Certifications:** {', '.join(resume['certifications'])}")

    if resume.get("raw_text"):
        lines.append(f"\n**Full CV Excerpt (first 1500 chars):**\n{resume['raw_text'][:1500]}")

    return "\n".join(lines)


# ── Prior Session Context ──────────────────────────────────────────────────────

def build_prior_session_context(
    conversation_id: str, current_session_id: str, db: Session
) -> str:
    messages = chat_db.get_other_sessions_messages(db, conversation_id, current_session_id)
    if not messages:
        return ""

    history_lines = []
    for msg in messages[-30:]:
        prefix = "User" if msg.role == "user" else "Coach"
        history_lines.append(f"{prefix}: {msg.content[:400]}")

    return "\n".join(history_lines)


# ── System Prompt ──────────────────────────────────────────────────────────────

def build_system_prompt(
    cv_context: str,
    prior_session_context: str,
    past_summaries: list[str],
) -> str:
    parts = [
        "You are Praxis, an expert AI career coach. Your sole purpose is to help the user "
        "strengthen their CV, identify career gaps, and provide actionable advice.",
        "Always ground your advice in the user's actual CV data provided below. "
        "Be warm, specific, and avoid generic career advice.",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📄  USER'S CURRENT CV",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        cv_context,
    ]

    if past_summaries:
        summaries_block = "\n".join(f"• {s.strip()}" for s in past_summaries if s)
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🗂  KEY OUTCOMES FROM PREVIOUS CONVERSATIONS",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            summaries_block,
        ]

    if prior_session_context:
        parts += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "💬  EARLIER CHATS IN THIS CONVERSATION",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            prior_session_context,
        ]

    parts += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📋  YOUR RESPONSE FORMAT  (always follow this structure exactly)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "## 🎯 Quick Summary",
        "[1-2 sentence direct answer to the user's question, referencing their CV]",
        "",
        "## 💡 Key Suggestions",
        "- [Specific, actionable suggestion — tied to their actual skills/experience]",
        "- [Another suggestion]",
        "",
        "## 📋 Detailed Breakdown",
        "[In-depth explanation with concrete examples using their CV content]",
        "",
        "## ✅ Next Steps",
        "- [Immediate concrete action they can take]",
        "- [Follow-up action]",
        "",
        "Keep responses focused and specific. Reference their actual job titles, skills, "
        "and projects. Never give generic advice that could apply to anyone.",
    ]

    return "\n".join(parts)


# ── Main Chat Orchestrator (legacy path) ───────────────────────────────────────

async def generate_chat_response(
    user_message: str,
    session_id: str,
    conversation_id: str,
    user_id: str,
    db: Session,
) -> dict:
    cv_context = build_cv_context(user_id, db)

    all_conversations = chat_db.get_conversations(db, user_id)
    past_summaries = [
        c.summary
        for c in all_conversations
        if c.id != conversation_id and c.summary
    ]

    prior_session_context = build_prior_session_context(conversation_id, session_id, db)
    system_prompt = build_system_prompt(cv_context, prior_session_context, past_summaries)

    current_messages = chat_db.get_session_messages(db, session_id)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in current_messages:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    raw_content = await call_llm(messages=messages, temperature=0.7)

    chat_db.save_message(db, session_id, "user", user_message)
    saved_assistant = chat_db.save_message(db, session_id, "assistant", raw_content)

    return {
        "message": saved_assistant,
        "raw_content": raw_content,
        "session_id": session_id,
        "conversation_id": conversation_id,
    }


# ── Conversation Summarizer ────────────────────────────────────────────────────

async def generate_conversation_summary(conversation_id: str, db: Session) -> str:
    all_messages = chat_db.get_conversation_all_messages(db, conversation_id)
    if not all_messages:
        return "No messages in this conversation yet."

    transcript_lines = []
    for msg in all_messages[-40:]:
        prefix = "User" if msg.role == "user" else "Coach"
        transcript_lines.append(f"{prefix}: {msg.content[:500]}")
    transcript = "\n".join(transcript_lines)

    prompt_messages = [
        {
            "role": "system",
            "content": (
                "You are summarizing a career coaching session. "
                "Extract 3-5 concise bullet points covering:\n"
                "- Key skill gaps or weaknesses identified\n"
                "- Strengths and positives acknowledged\n"
                "- Specific action items or advice given\n"
                "- Topics the user wants to improve\n"
                "Be specific — mention actual skills, roles, or areas discussed. "
                "This summary will be used as memory for future coaching sessions."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize the key outcomes from this coaching conversation:\n\n{transcript}",
        },
    ]

    summary = await call_llm(messages=prompt_messages, temperature=0.3)
    chat_db.update_conversation_summary(db, conversation_id, summary)
    return summary


# ── Compressed context builders (token-efficient) ─────────────────────────────

def build_compressed_cv_context(user_id: str) -> str:
    try:
        resume = fetch_resume_from_db(user_id)
    except Exception:
        return "No CV uploaded yet. Ask the user to upload their CV first."

    parts = []
    name = resume.get("name", "")
    location = resume.get("location", "")
    yoe = resume.get("years_of_experience", "")
    header = " | ".join(filter(None, [name, location, f"{yoe} yrs exp" if yoe else ""]))
    if header:
        parts.append(header)

    if resume.get("skills"):
        parts.append("Skills: " + ", ".join(resume["skills"]))

    if resume.get("experience"):
        exp_lines = [
            f"  {e.get('role', '')} @ {e.get('organization', '')}"
            for e in resume["experience"]
        ]
        parts.append("Experience:\n" + "\n".join(exp_lines))

    if resume.get("education"):
        edu_lines = [
            f"  {e.get('degree', '')} @ {e.get('institution', '')}"
            for e in resume["education"]
        ]
        parts.append("Education:\n" + "\n".join(edu_lines))

    if resume.get("certifications"):
        parts.append("Certs: " + ", ".join(resume["certifications"]))

    return "\n".join(parts)


def build_job_context(job, fit_score: dict | None = None) -> str:
    parts = [
        f"Job ID: {job.id}",
        f"Job: {job.title} @ {job.company_name}",
        f"Location: {job.location or 'Remote'} | Level: {job.experience_level or 'Not specified'}",
    ]
    if job.salary:
        parts.append(f"Salary: {job.salary}")

    if fit_score:
        parts.append(
            f"Your match: {fit_score.get('fit_score', '?')}% — {fit_score.get('verdict', '')}"
        )
        strengths = fit_score.get("strengths", [])
        weaknesses = fit_score.get("weaknesses", [])
        if strengths:
            parts.append("You match: " + ", ".join(strengths[:6]))
        if weaknesses:
            parts.append("You're missing: " + ", ".join(weaknesses[:6]))

    if job.skills_and_technologies:
        parts.append("Required skills: " + ", ".join((job.skills_and_technologies or [])[:10]))

    summary = (job.description or "")[:400]
    if summary:
        parts.append(f"About role: {summary}")

    return "\n".join(parts)


def build_efficient_system_prompt(
    cv_context: str,
    context_type: str,
    job_context: str | None,
    last_session_summary: str | None,
    tools_available: bool,
    cv_evidence: str | None = None,
    pending_description: str | None = None,
) -> str:
    parts = [
        "You are Praxis, an AI career co-pilot. You help users with career advice, job search, "
        "skill development, and application tracking.",
        "Ground all advice in the user's real CV data. Never invent skills, roles, or experience.",
        "",
        "━━━ TOOL RULES (CRITICAL) ━━━",
        "",
        "WHAT YOU CAN DO WITH TOOLS:",
        "• search_jobs(query, location) — find real live job listings. ALWAYS call this tool when",
        "  the user asks to search, find, or look up jobs. NEVER write fake job listings.",
        "• get_my_applications() — retrieve the user's tracked job applications.",
        "• get_my_goals() — retrieve the user's active career goals.",
        "• get_my_roadmaps() — retrieve the user's career roadmaps.",
        "• get_fit_score(job_id) — analyze how well the user fits a specific job. REQUIRES a job.",
        "• generate_roadmap(source, job_id?) — create a career roadmap. WRITE TOOL.",
        "• create_goals(roadmap_id, milestone_ids) — create goals from a roadmap. WRITE TOOL.",
        "• save_to_tracker(job_id) — save a job to the application tracker. WRITE TOOL. REQUIRES a job.",
        "• draft_cover_letter(job_id, tone?) — write a cover letter. WRITE TOOL. REQUIRES a job.",
        "• update_application_status(application_id, new_status) — update tracker. WRITE TOOL.",
        "• add_application_note(application_id, content) — add a note to an application. WRITE TOOL.",
        "",
        "WHAT YOU CANNOT DO (say this clearly if asked):",
        "• Apply to jobs on the user's behalf",
        "• Send emails or messages to recruiters",
        "• Edit the user's CV directly",
        "• Access external websites or LinkedIn",
        "• Remember past conversations beyond what's shown in context",
        "• For anything not listed above, say: 'I can't do that from here — please use the app directly.'",
        "",
        "READ tools: call immediately, no confirmation needed.",
        "WRITE tools: ALWAYS call request_confirmation first with action_description,",
        "  pending_tool (exact tool name), and pending_args (tool arguments JSON).",
        "  Only execute the write tool after user confirms.",
        "  EXCEPTION: if ━━━ AWAITING CONFIRMATION ━━━ is present below, execute the",
        "  pending write tool directly — do NOT call request_confirmation again.",
        "",
        "JOB-REQUIRED TOOLS (get_fit_score, save_to_tracker, draft_cover_letter,",
        "update_application_status, add_application_note) REQUIRE a specific job.",
        "If the user asks to use one of these but no job is in context, respond:",
        "\"To do that I need to know which job you mean. Try: 'search for [role] jobs' first.\"",
        "Then call search_jobs if they provide a query.",
        "",
        "━━━ HONESTY RULES ━━━",
        "• NEVER invent job listings, companies, salaries, application data, or any information.",
        "• NEVER simulate a tool call in text (e.g. writing 'SEARCHING...' without calling the tool).",
        "• NEVER write 'I found X jobs at Company Y' without the search_jobs tool having actually run.",
        "• If a tool returns no results, say so honestly.",
        "• Never reveal internal tool names or system implementation details to the user.",
        "",
        "━━━ RESPONSE STYLE ━━━",
        "• NEVER present options as A/B/C or numbered choice menus. Respond naturally.",
        "• After a READ tool: summarize the REAL results in 2-3 conversational sentences.",
        "• After a WRITE tool: confirm what was done in 1-2 sentences.",
        "• For career advice (no tool needed): Quick Summary → Key Suggestions → Next Steps.",
        "• Keep responses focused. Reference the user's actual CV data only.",
    ]

    if pending_description:
        parts += [
            "",
            "━━━ AWAITING CONFIRMATION ━━━",
            f"You previously asked the user to confirm: {pending_description}",
            "If their message confirms this, execute the pending write tool directly (no request_confirmation).",
            "If they cancel, respond conversationally and do not execute anything.",
        ]

    if cv_evidence:
        parts += ["", "━━━ RETRIEVED CV EVIDENCE (source of truth for CV details) ━━━", cv_evidence]

    parts += ["", "━━━ USER CV ━━━", cv_context]

    if context_type == "job" and job_context:
        parts += ["", "━━━ JOB YOU'RE DISCUSSING ━━━", job_context]

    if last_session_summary:
        parts += ["", "━━━ RECENT COACHING NOTES ━━━", last_session_summary]

    return "\n".join(parts)


# ── Unified send_message ───────────────────────────────────────────────────────

async def send_message(
    content: str,
    user_id: str,
    db: Session,
    job_id: str | None = None,
) -> dict:
    from app.modules.chat.tools import get_tools_for_context, execute_tool

    # 1. Find or create conversation
    if job_id:
        conv = chat_db.get_or_create_job_conversation(db, user_id, job_id)
    else:
        conv = chat_db.get_or_create_general_conversation(db, user_id)

    # 2. Find or create active session
    session = chat_db.get_or_create_active_session(db, conv.id)
    session_id = session.id
    conversation_id = conv.id

    # 2b. Check Redis for a pending confirmation from the previous turn
    pending_key = f"pending_tool:{session_id}"
    r_pend = aioredis.from_url(settings.REDIS_URL)
    try:
        pending_raw = await r_pend.get(pending_key)
    except Exception:
        pending_raw = None
    finally:
        await r_pend.aclose()
    pending = json.loads(pending_raw) if pending_raw else None

    # 3. Build structured CV context (token-efficient summary)
    cv_context = build_compressed_cv_context(user_id)

    job_context = None
    fit_score = None
    job = None
    if job_id:
        from app.modules.jobs.models import Job
        from app.modules.jobs.services.fit_scorer import compute_fit_score
        from app.modules.jobs.services.job_suggestion import _job_to_profile
        from app.modules.CV.schemas import ResumeSchema
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            try:
                resume_data = fetch_resume_from_db(user_id)
                candidate = ResumeSchema(**resume_data)
                profile = _job_to_profile(job)
                fs = await compute_fit_score(profile=profile, candidate=candidate)
                fit_score = {
                    "fit_score": fs.fit_score,
                    "verdict": fs.verdict,
                    "strengths": fs.strengths,
                    "weaknesses": fs.weaknesses,
                }
            except Exception:
                pass
            job_context = build_job_context(job, fit_score)

    # 3b. RAG: retrieve section-level CV evidence for this specific query
    from app.modules.CV.rag_service import retrieve_cv_evidence
    if job_id and job:
        rag_query = (
            f"User question: {content}\n"
            f"Job: {job.title} at {job.company_name}\n"
            f"Required skills: {', '.join(job.skills_and_technologies or [])}"
        )
    else:
        rag_query = content

    cv_evidence = await retrieve_cv_evidence(db, user_id, rag_query)

    # 4. Last session summary for cross-session memory
    all_sessions = chat_db.get_session_summaries(db, conversation_id)
    last_summary = next(
        (s.session_summary for s in all_sessions if not s.is_active and s.session_summary),
        None,
    )

    context_type = conv.context_type
    tools = get_tools_for_context(context_type)

    pending_description = pending.get("description") if pending else None
    system_prompt = build_efficient_system_prompt(
        cv_context=cv_context,
        context_type=context_type,
        job_context=job_context,
        last_session_summary=last_summary,
        tools_available=True,
        cv_evidence=cv_evidence if cv_evidence else None,
        pending_description=pending_description,
    )

    # 5. Build messages array (last 10 from current session)
    recent = chat_db.get_session_messages(db, session_id)[-10:]

    # 5b. Confirmation / cancellation short-circuit (Python-side, no LLM round-trip)
    if pending and _is_cancellation(content):
        await _clear_pending(session_id)
        cancel_msg = "Got it — I've cancelled that. Let me know if there's anything else I can help with."
        chat_db.save_message(db, session_id, "user", content)
        saved = chat_db.save_message(db, session_id, "assistant", cancel_msg)
        chat_db.increment_message_count(db, session_id)
        return {
            "content": cancel_msg,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "created_at": saved.created_at,
            "tool_status": "handled",
            "ui_payload": None,
            "notification": None,
        }

    if pending and _is_confirmation(content) and pending.get("tool_name"):
        await _clear_pending(session_id)
        tool_result = await execute_tool(
            tool_name=pending["tool_name"],
            tool_args=pending["tool_args"],
            user_id=user_id,
            conversation_id=conversation_id,
            db=db,
        )
        # LLM wraps the tool result into a brief confirmation sentence
        wrap_msgs = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role, "content": m.content} for m in recent],
            {"role": "user", "content": content},
            {"role": "tool", "tool_call_id": "confirmed", "content": tool_result.message},
            {"role": "user", "content": "Briefly confirm to the user what was just done (1-2 sentences)."},
        ]
        try:
            final_content = await call_llm(messages=wrap_msgs, temperature=0.5)
            if not isinstance(final_content, str):
                final_content = tool_result.message
        except Exception:
            final_content = tool_result.message

        chat_db.save_message(db, session_id, "user", content)
        saved = chat_db.save_message(db, session_id, "assistant", final_content)
        new_count = chat_db.increment_message_count(db, session_id)
        if new_count >= SESSION_ROTATION_THRESHOLD:
            asyncio.create_task(
                _auto_summarize_and_rotate(session_id, conversation_id, user_id, context_type, db)
            )

        notification_id = None
        if tool_result.should_notify:
            from app.modules.notifications.service import create_and_publish as notify
            try:
                notification_id = await notify(
                    user_id=user_id,
                    type=tool_result.notification_type,
                    title=tool_result.notification_title,
                    message=tool_result.notification_message,
                    data=tool_result.notification_data,
                )
            except Exception:
                pass

        return {
            "content": final_content,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "created_at": saved.created_at,
            "tool_status": tool_result.status,
            "ui_payload": (
                {"type": tool_result.payload_type, "data": tool_result.payload}
                if tool_result.payload_type else None
            ),
            "notification": {"created": True, "notification_id": notification_id} if notification_id else None,
        }

    # Ambiguous message while pending — clear stale state (AWAITING prompt already injected above)
    if pending:
        await _clear_pending(session_id)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in recent:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": content})

    # 6. Agentic loop — returns (content, tool_result, notification_id, pending_info)
    final_content, tool_result, notification_id, pending_info = await _agentic_loop(
        messages=messages,
        tools=tools,
        user_id=user_id,
        conversation_id=conversation_id,
        db=db,
    )

    # 6b. Store pending_info so the next turn can short-circuit
    if pending_info:
        r_store = aioredis.from_url(settings.REDIS_URL)
        try:
            await r_store.setex(pending_key, 1800, json.dumps(pending_info))
        except Exception:
            pass
        finally:
            await r_store.aclose()

    # 7. Persist both turns
    chat_db.save_message(db, session_id, "user", content)
    saved = chat_db.save_message(db, session_id, "assistant", final_content)

    # 8. Increment count; trigger background rotation if threshold reached
    new_count = chat_db.increment_message_count(db, session_id)
    if new_count >= SESSION_ROTATION_THRESHOLD:
        asyncio.create_task(
            _auto_summarize_and_rotate(session_id, conversation_id, user_id, context_type, db)
        )

    # 9. Build extended response
    return {
        "content": final_content,
        "session_id": session_id,
        "conversation_id": conversation_id,
        "created_at": saved.created_at,
        "tool_status": tool_result.status if tool_result else "handled",
        "ui_payload": (
            {"type": tool_result.payload_type, "data": tool_result.payload}
            if (tool_result and tool_result.payload_type) else None
        ),
        "notification": (
            {"created": True, "notification_id": notification_id}
            if notification_id else None
        ),
    }


# ── Agentic loop ───────────────────────────────────────────────────────────────

async def _agentic_loop(
    messages: list[dict],
    tools: list[dict],
    user_id: str,
    conversation_id: str,
    db: Session,
    max_rounds: int = 5,
) -> tuple[str, ToolExecutionResult | None, str | None, dict | None]:
    """
    Run the LLM with function calling.
    Returns (final_content, last_tool_result, notification_id, pending_info).

    Special behaviors:
    - request_confirmation: exits the loop immediately, returns action description as content
      and pending_info dict (tool_name, tool_args, description) for Redis storage
    - should_notify: fires notification inline and captures the notification_id
    - Multiple tool calls in one round: stops batch on first confirmation_required
    """
    from app.modules.chat.tools import execute_tool
    from app.modules.notifications.service import create_and_publish as notify

    last_tool_result: ToolExecutionResult | None = None
    notification_id: str | None = None

    for _ in range(max_rounds):
        try:
            raw = await call_llm(messages=messages, temperature=0.7, tools=tools)
        except TypeError:
            raw = await call_llm(messages=messages, temperature=0.7)
            return raw, last_tool_result, notification_id, None
        except ChatbotCallerError as e:
            if e.status_code == 400 and tools:
                raw = await call_llm(messages=messages, temperature=0.7)
                return raw, last_tool_result, notification_id, None
            raise

        # Plain text response — done
        if isinstance(raw, str):
            return raw, last_tool_result, notification_id, None

        # Tool call response
        if isinstance(raw, dict) and raw.get("tool_calls"):
            tool_calls = raw["tool_calls"]
            # Preserve any text the LLM wrote alongside the tool call
            assistant_text = raw.get("content") or None
            messages.append({"role": "assistant", "content": assistant_text, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"].get("arguments", "{}"))
                result = await execute_tool(
                    tool_name=fn_name,
                    tool_args=fn_args,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    db=db,
                )

                if result.status == "confirmation_required":
                    # Exit loop — store what the LLM declared it will do next
                    response_content = assistant_text or result.message
                    pending_info = None
                    pending_tool_name = fn_args.get("pending_tool")
                    if pending_tool_name:
                        pending_info = {
                            "tool_name": pending_tool_name,
                            "tool_args": fn_args.get("pending_args") or {},
                            "description": result.message,
                        }
                    return response_content, result, None, pending_info

                # Fire notification inline for write tools
                if result.should_notify:
                    try:
                        notification_id = await notify(
                            user_id=user_id,
                            type=result.notification_type,
                            title=result.notification_title,
                            message=result.notification_message,
                            data=result.notification_data,
                        )
                    except Exception as e:
                        print(f"[Chat] Notification failed: {e}")

                last_tool_result = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result.message,
                })

            continue  # loop back for LLM final response

        # Unexpected shape
        return str(raw), last_tool_result, notification_id, None

    return "I encountered an issue processing your request. Please try again.", last_tool_result, notification_id, None


# ── Background session rotation ────────────────────────────────────────────────

async def _auto_summarize_and_rotate(
    session_id: str,
    conversation_id: str,
    user_id: str,
    context_type: str,
    db: Session,
) -> None:
    from app.core.session import SessionLocal
    try:
        with SessionLocal() as bg_db:
            all_messages = chat_db.get_conversation_all_messages(bg_db, conversation_id)
            if not all_messages:
                return

            transcript_lines = []
            for msg in all_messages[-30:]:
                prefix = "User" if msg.role == "user" else "Coach"
                transcript_lines.append(f"{prefix}: {msg.content[:400]}")

            prompt_messages = [
                {
                    "role": "system",
                    "content": (
                        "Summarize this career coaching session in 3-4 concise bullet points covering: "
                        "skill gaps identified, strengths noted, advice given, and action items. "
                        "Be specific — mention actual skills and roles. Max 150 words."
                    ),
                },
                {"role": "user", "content": "\n".join(transcript_lines)},
            ]
            summary = await call_llm(messages=prompt_messages, temperature=0.3)
            chat_db.save_session_summary(bg_db, session_id, summary)
            chat_db.prune_old_messages(bg_db, conversation_id, keep_sessions=2)

            gap_keywords = {"missing", "gap", "need to learn", "lacking", "improve", "develop"}
            if context_type == "job" and any(kw in summary.lower() for kw in gap_keywords):
                from app.modules.notifications.service import create_and_publish as notify
                await notify(
                    user_id=user_id,
                    type="coach_roadmap_nudge",
                    title="Ready to close your skill gaps?",
                    message="Your coaching session identified growth areas. Want me to build a roadmap?",
                    data={"conversation_id": conversation_id},
                )
    except Exception as e:
        print(f"[Chat] Auto-summarize failed for session {session_id}: {e}")
