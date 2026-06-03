from app.modules.CV.schemas import ResumeSchema
from app.modules.fit_score.schema import (
    CandidateFitProfile,
    FitScoreRequest,
    FitScoreResponse,
    JobDetailWithFitResponse,
)
from app.modules.jobs.schema import (
    ApplyOption,
    EmployerReview,
    JobCard,
    JobDetailResponse,
    JobHighlights,
    JobRequirementProfile,
    JobRequirementProfileResponse,
    JobSearchRequest,
    JobSearchResponse,
    RequiredExperience,
    SalaryInfo,
)


__all__ = (
    "ApplyOption",
    "EmployerReview",
    "JobCard",
    "JobDetailResponse",
    "JobHighlights",
    "JobSearchRequest",
    "JobSearchResponse",
    "RequiredExperience",
    "SalaryInfo",
    "JobRequirementProfile",
    "JobRequirementProfileResponse",
    "ResumeSchema",
    "CandidateFitProfile",
    "FitScoreResponse",
    "FitScoreRequest",
    "JobDetailWithFitResponse",
)