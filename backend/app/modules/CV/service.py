import json
import os
from openai import OpenAI
from app.schemas import ResumeSchema
from app.core.config import settings
import re
client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


async def extract_resume_with_grok(raw_text: str):

    prompt = f"""
You are an expert ATS resume parser.

Extract structured information from the resume.

Return ONLY valid JSON (no explanation, no markdown).

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

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3-0324",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a professional ATS resume parser that outputs ONLY valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    parsed_json = safe_json_parse(content)

    parsed_json["raw_text"] = raw_text

    return ResumeSchema(**parsed_json)


def safe_json_parse(text: str):
    text = text.strip()

    # remove markdown fences
    text = text.replace("```json", "").replace("```", "")

    # extract only JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON found in model output")

    return json.loads(match.group(0))