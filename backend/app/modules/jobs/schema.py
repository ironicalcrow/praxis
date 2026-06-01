from typing import Optional
from pydantic import BaseModel

class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    page: int = 1
    num_pages: int = 1


class JobCard(BaseModel):
    external_id: Optional[str] = None
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    deadline: Optional[str] = None
    description: Optional[str] = None
    job_url: Optional[str] = None
    source: str = "jsearch"
    posted_at: Optional[str] = None


class JobSearchResponse(BaseModel):
    query: str
    total: int
    jobs: list[JobCard]