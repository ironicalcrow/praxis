from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime

class RawScrapedJob(BaseModel):
    """
    Represents the raw data scraped from a job board before LLM processing.
    """
    provider_id: str  # e.g., 'linkedin', 'bdjobs', 'glassdoor'
    job_id: str       # Original ID from the platform to prevent duplicates
    title: str
    company_name: str
    location: Optional[str] = None
    url: HttpUrl
    raw_html_content: Optional[str] = None # The messy HTML description to be fed to LLM
    raw_text_content: Optional[str] = None # Fallback text content if HTML isn't available
    search_query_id: Optional[str] = None
    raw_json_data: Optional[Dict[str, Any]] = None
    posted_at: Optional[datetime] = None
    is_active: bool = True
