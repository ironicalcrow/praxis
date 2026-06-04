import json
import re

from fastapi import HTTPException

from app.schemas import ResumeSchema
from app.core.llm_caller import call_llm, LLMCallerError


async def extract_resume_with_grok(raw_text: str):

    prompt = f"""
You are an expert ATS resume parser.

Extract structured information from the resume.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanation.

Schema:
{{
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "years_of_experience": 0
}}

Resume:
{raw_text}
"""

    messages = [
        {
            "role": "system",
            "content": "You are a professional ATS resume parser that outputs ONLY valid JSON.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    try:
        content = await call_llm(
            messages=messages,
            model="deepseek/deepseek-chat-v3-0324",
            temperature=0.0,
            json_mode=True,
        )

        parsed_json = safe_json_parse(content)

        parsed_json["raw_text"] = raw_text

        return ResumeSchema(**parsed_json)

    except LLMCallerError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM resume extraction failed: {str(e)}",
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM JSON response: {str(e)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Resume extraction failed: {str(e)}",
        )


def safe_json_parse(text: str):

    if not text:
        raise ValueError("Empty model output")

    text = text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON found in model output")

    return json.loads(match.group(0))