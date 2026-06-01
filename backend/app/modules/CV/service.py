import json
import os
from openai import OpenAI
from app.schemas import ResumeSchema

client = OpenAI(
     api_key=os.getenv("XAI_API_KEY"),
     base_url="https://api.x.ai/v1",)

async def extract_resume_with_grok(raw_text: str): 
     prompt = f"""You are an expert ATS resume parser. Extract information from the resume. Return ONLY valid JSON. Schema: {{
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "skills": [],
        "education": [],]
        "experience": [],]
        "projects": [],
        "certifications": [],
        "years_of_experience": 0}}
        Resume: {raw_text} """
     response = client.chat.completions.create( model="grok-3-mini", temperature=0, messages=[{ "role": "system", "content": "You are a professional ATS parser.",},{
         "role": "user",
         "content": prompt,
         },],)
     content = response.choices[0].message.content
     parsed_json = json.loads(content)
     parsed_json["raw_text"] = raw_text
     return ResumeSchema(**parsed_json)