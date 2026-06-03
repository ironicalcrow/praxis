from app.modules.jobs.schema import JobCard, JobSearchRequest, JobSearchResponse
from app.modules.CV.schemas import ResumeSchema
from app.modules.jobs.schema import (
    ApplyOption,
    EmployerReview,
    JobCard,
    JobDetailResponse,
    JobHighlights,
    JobSearchRequest,
    JobSearchResponse,
    RequiredExperience,
    SalaryInfo,
    JobRequirementProfile,
    JobRequirementProfileResponse
)

from app.modules.fit_score.schema import(
    CandidateFitProfile,
    FitScoreResponse,
    FitScoreRequest,
    JobDetailWithFitResponse,
)


__all__ = (
    "ApplyOption",
    "EmployerReview",
    "JobCard",
    "JobDetailResponse",
    "JobHighlights",
    "JobSearchRequest",
    "JobSearchResponse",
    "ResumeSchema",
)

    "RequiredExperience",
    "SalaryInfo",
    "CandidateFitProfile",
    "FitScoreResponse",
    "FitScoreRequest",
    "JobDetailWithFitResponse",
    "JobRequirementProfile",
    "JobRequirementProfileResponse",
)