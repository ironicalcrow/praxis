from sqlalchemy.orm import Session

from app.core.chatbot_caller import call_chatbot as call_llm
from app.modules.chat import db_service as chat_db
from app.modules.CV.db_service import fetch_resume_from_db


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

    # Include a raw excerpt for deeper semantic grounding
    if resume.get("raw_text"):
        lines.append(f"\n**Full CV Excerpt (first 1500 chars):**\n{resume['raw_text'][:1500]}")

    return "\n".join(lines)


# ── Prior Session Context ──────────────────────────────────────────────────────

def build_prior_session_context(
    conversation_id: str, current_session_id: str, db: Session
) -> str:
    """
    Summarizes messages from earlier sessions in the same conversation
    so the LLM maintains continuity across chats within the same topic.
    """
    messages = chat_db.get_other_sessions_messages(db, conversation_id, current_session_id)
    if not messages:
        return ""

    history_lines = []
    for msg in messages[-30:]:  # cap at 30 cross-session messages for token safety
        prefix = "User" if msg.role == "user" else "Coach"
        history_lines.append(f"{prefix}: {msg.content[:400]}")

    return "\n".join(history_lines)


# ── System Prompt ──────────────────────────────────────────────────────────────

def build_system_prompt(
    cv_context: str,
    prior_session_context: str,
    past_summaries: list[str],
) -> str:
    """
    Assembles the full system prompt with:
    - Role definition
    - CV context (RAG)
    - Cross-conversation memory (past summaries)
    - Within-conversation context (prior sessions)
    - Response format rules
    """
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


# ── Main Chat Orchestrator ─────────────────────────────────────────────────────

async def generate_chat_response(
    user_message: str,
    session_id: str,
    conversation_id: str,
    user_id: str,
    db: Session,
) -> dict:
    """
    Full pipeline:
      1. Build CV context (RAG — grounded in DB resume)
      2. Fetch past conversation summaries (cross-conversation memory)
      3. Fetch prior sessions in this conversation (within-conversation continuity)
      4. Assemble system prompt
      5. Build full message history for this session
      6. Call LLM
      7. Persist both the user message and assistant reply
      8. Return structured response dict
    """
    # 1. CV context (RAG)
    cv_context = build_cv_context(user_id, db)

    # 2. Cross-conversation memory: summaries from all OTHER conversations
    all_conversations = chat_db.get_conversations(db, user_id)
    past_summaries = [
        c.summary
        for c in all_conversations
        if c.id != conversation_id and c.summary
    ]

    # 3. Within-conversation context: prior sessions
    prior_session_context = build_prior_session_context(conversation_id, session_id, db)

    # 4. System prompt
    system_prompt = build_system_prompt(cv_context, prior_session_context, past_summaries)

    # 5. Build messages array: system + current session history + new user message
    current_messages = chat_db.get_session_messages(db, session_id)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in current_messages:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    # 6. Call LLM
    raw_content = await call_llm(messages=messages, temperature=0.7)

    # 7. Persist both turns
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
    """
    Reads all messages across all sessions in the conversation,
    asks the LLM to extract key career insights in bullet-point form,
    then saves the summary to chat_conversations.summary.

    This summary is later injected into future conversations as
    cross-conversation memory.
    """
    all_messages = chat_db.get_conversation_all_messages(db, conversation_id)
    if not all_messages:
        return "No messages in this conversation yet."

    # Build condensed transcript (capped for token budget)
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
            "content": (
                f"Summarize the key outcomes from this coaching conversation:\n\n{transcript}"
            ),
        },
    ]

    summary = await call_llm(messages=prompt_messages, temperature=0.3)
    chat_db.update_conversation_summary(db, conversation_id, summary)
    return summary
