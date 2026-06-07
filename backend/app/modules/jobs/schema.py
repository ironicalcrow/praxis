from typing import Any, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, PrivateAttr, Field, field_validator

from app.core.utils import UUIDStr

class JobTypeEnum(str, Enum):
    # Employment type
    FULL_TIME   = "Full-time"
    PART_TIME   = "Part-time"
    CONTRACT    = "Contract"
    INTERNSHIP  = "Internship"
    FREELANCE   = "Freelance"
    # Work arrangement
    REMOTE      = "Remote"
    HYBRID      = "Hybrid"
    ONSITE      = "On-site"

class UserPreferenceCreate(BaseModel):
    job_types: list[JobTypeEnum] = Field(default_factory=list)

class UserPreferenceUpdate(BaseModel):
    job_types: Optional[list[JobTypeEnum]] = None

class UserPreferenceResponse(BaseModel):
    id: str
    user_id: UUIDStr
    job_types: list[str] = Field(default_factory=list)

class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    page: int = 1
    num_pages: int = 1
    country: str = "bd"
    remote_jobs_only: Optional[bool] = None

class SuggestionWindowResponse(BaseModel):
    jobs: list['JobSchema']
    jobs_seen: int
    pool_total: int
    prefetch_triggered: bool = False
    pool_cycling: bool = False


class JobQuerySchema(BaseModel):
    query: str
    reason: Optional[str] = None
    priority: Optional[int] = None


class FitScoreResponse(BaseModel):
    fit_score: float
    verdict: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    reason: str


class JobSchema(BaseModel):
    id: Optional[str] = None
    
    external_id: str
    provider_id: str
    
    fit_score: Optional[FitScoreResponse] = None
    
    title: str
    job_types: list[str] = Field(default_factory=list)
    
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    publisher: Optional[str] = None
    
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    
    posted_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    salary: Optional[str] = None
    experience_level: Optional[str] = None
    
    apply_urls: list[str] = Field(default_factory=list)
    
    description: Optional[str] = None
    llm_summary: Optional[str] = None
    skills_and_technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)

class JobRequirementProfile(BaseModel):
    summary: str | None = None

    description: str | None = None

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    tools_and_technologies: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)

    required_experience_years: float | None = None
    seniority_level: str | None = None

    job_function: str | None = None
    industry: str | None = None
    work_arrangement: str | None = None

    education_requirements: list[str] = Field(default_factory=list)
    important_context: list[str] = Field(default_factory=list)

    @field_validator(
        "required_skills", "preferred_skills", "tools_and_technologies",
        "methodologies", "soft_skills", "responsibilities", "qualifications",
        "benefits", "education_requirements", "important_context",
        mode="before"
    )
    @classmethod
    def force_list(cls, v):
        if not v:
            return []
        if isinstance(v, str):
            return [v]
        return v



class JobSearchResponse(BaseModel):
    query: str
    total: int
    jobs: list['JobSchema']
