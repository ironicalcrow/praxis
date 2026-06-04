from typing import Any, Optional

from pydantic import BaseModel, PrivateAttr,Field

class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    page: int = 1
    num_pages: int = 1
    country: str = "bd"
    date_posted: str = "all"


class ApplyOption(BaseModel):
    publisher: Optional[str] = None
    apply_link: Optional[str] = None
    is_direct: Optional[bool] = None


class SalaryInfo(BaseModel):
    salary_text: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None


class JobHighlights(BaseModel):
    qualifications: list[str] = []
    responsibilities: list[str] = []
    benefits: list[str] = []


class RequiredExperience(BaseModel):
    no_experience_required: Optional[bool] = None
    required_experience_in_months: Optional[int] = None
    experience_mentioned: Optional[bool] = None
    experience_preferred: Optional[bool] = None


class EmployerReview(BaseModel):
    publisher: Optional[str] = None
    employer_name: Optional[str] = None
    score: Optional[float] = None
    num_stars: Optional[float] = None
    review_count: Optional[int] = None
    max_score: Optional[float] = None
    reviews_link: Optional[str] = None


class JobCard(BaseModel):
    external_id: str
    title: str
    company: Optional[str] = None
    company_logo: Optional[str] = None
    company_website: Optional[str] = None

    publisher: Optional[str] = None
    employment_type: Optional[str] = None
    employment_types: list[str] = []

    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: Optional[bool] = None

    apply_url: Optional[str] = None
    is_direct_apply: Optional[bool] = None

    description_preview: Optional[str] = None

    posted_at: Optional[str] = None
    posted_human_readable: Optional[str] = None
    deadline: Optional[str] = None

    salary: Optional[SalaryInfo] = None
    source: str = "jsearch"

    _raw_payload: Optional[dict[str, Any]] = PrivateAttr(default=None)

    def set_raw_payload(self, payload: dict[str, Any]) -> None:
        self._raw_payload = payload

    def get_raw_payload(self) -> Optional[dict[str, Any]]:
        return self._raw_payload


class JobDetailResponse(BaseModel):
    external_id: str
    title: str
    company: Optional[str] = None
    company_logo: Optional[str] = None
    company_website: Optional[str] = None

    publisher: Optional[str] = None
    employment_type: Optional[str] = None
    employment_types: list[str] = []

    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_remote: Optional[bool] = None
    work_arrangement: Optional[str] = None

    apply_url: Optional[str] = None
    is_direct_apply: Optional[bool] = None
    apply_options: list[ApplyOption] = []

    description: Optional[str] = None

    posted_at: Optional[str] = None
    posted_human_readable: Optional[str] = None
    deadline: Optional[str] = None

    salary: Optional[SalaryInfo] = None
    benefits: list[str] = []
    benefits_extended: list[str] = []

    highlights: JobHighlights = JobHighlights()
    required_experience: Optional[RequiredExperience] = None

    seniority_level: Optional[str] = None
    required_experience_years: Optional[int] = None
    required_technologies: list[str] = []
    preferred_technologies: list[str] = []
    methodologies: list[str] = []
    soft_skills: list[str] = []

    industry: Optional[str] = None
    job_function: Optional[str] = None
    ai_ml_involved: Optional[bool] = None
    has_management_responsibilities: Optional[bool] = None

    employer_reviews: list[EmployerReview] = []

    source: str = "jsearch"

    _raw_payload: Optional[dict[str, Any]] = PrivateAttr(default=None)

    def set_raw_payload(self, payload: dict[str, Any]) -> None:
        self._raw_payload = payload

    def get_raw_payload(self) -> Optional[dict[str, Any]]:
        return self._raw_payload

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

class JobRequirementProfileResponse(BaseModel):
    job_id: str
    profile: JobRequirementProfile

class JobSearchResponse(BaseModel):
    query: str
    total: int
    jobs: list[JobCard]

class JobSuggestionRequest(BaseModel):
    queries: list[str]
    location: Optional[str] = None
    country: str = "bd"
    page: int = 1
    num_pages: int = 1
    max_jobs_per_query: int = 10
    max_total_jobs: int = 30
