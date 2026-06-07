import re
from datetime import datetime
from typing import Any, List
from dateutil import parser as date_parser

from app.modules.jobs.schema import JobSchema
from app.providers.schemas import RawScrapedJob

# Common tech/soft skills for fast regex scanning
COMMON_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin",
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "flask", "fastapi", "spring boot", "ruby on rails",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra", "oracle", "sql server",
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "gitlab ci",
    "machine learning", "deep learning", "ai", "artificial intelligence", "nlp", "computer vision", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "data science",
    "html", "css", "sass", "tailwind", "bootstrap", "figma", "ui/ux", "graphql", "rest api", "grpc",
    "agile", "scrum", "kanban", "jira", "git", "linux", "bash", "powershell", "testing", "jest", "pytest", "selenium", "cypress",
    "communication", "leadership", "problem solving", "teamwork", "project management", "time management", "critical thinking"
]

def extract_skills_from_text(text: str) -> List[str]:
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = set()
    
    for skill in COMMON_SKILLS:
        # Use word boundaries to avoid partial matches (e.g., 'go' inside 'algorithm')
        # Handle special cases like c++ or node.js safely
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill.title() if skill.lower() not in ['sql', 'aws', 'gcp', 'ai', 'nlp', 'html', 'css', 'ui/ux', 'api'] else skill.upper())
            
    return list(found_skills)

def _parse_datetime(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        return date_parser.parse(date_str).replace(tzinfo=None)
    except Exception:
        return None

def parse_jsearch_to_schema(raw_job: RawScrapedJob) -> JobSchema:
    """
    Directly maps JSearch JSON object to JobSchema and extracts skills programmatically.
    """
    data: dict[str, Any] = raw_job.raw_json_data or {}
    
    # Extract basics
    title = data.get("job_title") or raw_job.title
    company_name = data.get("employer_name") or raw_job.company_name
    description = data.get("job_description") or raw_job.raw_text_content or ""
    
    # Location and Remote
    is_remote = data.get("job_is_remote", False)
    city = data.get("job_city", "")
    country = data.get("job_country", "")
    location_parts = [p for p in [city, country] if p]
    location = ", ".join(location_parts) if location_parts else raw_job.location
    if is_remote and "remote" not in location.lower():
        location = "Remote" if not location else f"{location} (Remote)"
        
    # Apply URLs
    apply_url = data.get("job_apply_link") or data.get("job_google_link") or raw_job.url
    apply_urls = [apply_url] if apply_url else []
    
    # Dates
    posted_at = _parse_datetime(data.get("job_posted_at_datetime_utc"))
    deadline = _parse_datetime(data.get("job_offer_expiration_datetime_utc"))
    
    # Job Types
    emp_type = data.get("job_employment_type")
    job_types = [emp_type] if emp_type else []
    
    # Publisher / Website
    publisher = data.get("job_publisher")
    company_website = data.get("employer_website")
    
    # Salary
    min_sal = data.get("job_min_salary")
    max_sal = data.get("job_max_salary")
    currency = data.get("job_salary_currency", "USD")
    period = data.get("job_salary_period", "YEAR")
    salary_str = None
    if min_sal and max_sal:
        salary_str = f"{min_sal} - {max_sal} {currency} per {period}"
    elif min_sal:
        salary_str = f"{min_sal}+ {currency} per {period}"
        
    # Highlights (Responsibilities / Qualifications)
    highlights = data.get("job_highlights", {})
    responsibilities = highlights.get("Responsibilities", [])
    qualifications = highlights.get("Qualifications", [])
    
    # Combine description with qualifications for better skill matching
    full_text_for_skills = f"{description}\n" + "\n".join(qualifications)
    skills = extract_skills_from_text(full_text_for_skills)
    
    # We create llm_summary by taking the first 300 chars of the description programmatically
    summary = description[:300] + "..." if len(description) > 300 else description

    return JobSchema(
        external_id=raw_job.job_id,
        provider_id=raw_job.provider_id,
        title=title,
        job_types=job_types,
        company_name=company_name,
        company_website=company_website,
        publisher=publisher,
        location=location,
        is_remote=is_remote,
        posted_at=posted_at or raw_job.posted_at,
        deadline=deadline,
        salary=salary_str,
        apply_urls=apply_urls,
        description=description,
        llm_summary=summary,
        skills_and_technologies=skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
        benefits=data.get("job_benefits") or [],
        metadata={"jsearch_raw": True}
    )
