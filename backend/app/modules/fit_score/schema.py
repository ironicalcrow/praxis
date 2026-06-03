from typing import Optional

from pydantic import BaseModel, Field

from app.modules.jobs.schema import JobDetailResponse, JobRequirementProfile


class CandidateProject(BaseModel):
    title: str
    description: str
    technologies: list[str] = Field(default_factory=list)


class CandidateFitProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

    projects: list[CandidateProject] = Field(default_factory=list)

    years_experience: Optional[float] = None
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_work_arrangement: Optional[str] = None

    summary: Optional[str] = None
    education: list[str] = Field(default_factory=list)


class FitScoreResponse(BaseModel):
    fit_score: float
    verdict: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    reason: str


class FitScoreRequest(BaseModel):
    candidate: CandidateFitProfile


class JobDetailWithFitResponse(BaseModel):
    job: JobDetailResponse

    # Keep this temporarily for debugging.
    # Remove before final/frontend response.
    job_requirement_profile: Optional[JobRequirementProfile] = None

    fit_score: FitScoreResponse