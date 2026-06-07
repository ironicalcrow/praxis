from app.modules.CV.schemas import ResumeSchema
from app.modules.jobs.schema import (
    JobSchema,
    JobRequirementProfile,
    JobSearchRequest,
    JobSearchResponse,
    FitScoreResponse,
    JobQuerySchema,
    JobTypeEnum,
    UserPreferenceCreate,
    UserPreferenceUpdate,
    UserPreferenceResponse,
    SuggestionWindowResponse,
)


__all__ = (
    "JobSchema",
    "JobSearchRequest",
    "JobSearchResponse",
    "JobRequirementProfile",
    "ResumeSchema",
    "FitScoreResponse",
    "JobQuerySchema",
    "JobTypeEnum",
    "UserPreferenceCreate",
    "UserPreferenceUpdate",
    "UserPreferenceResponse",
    "SuggestionWindowResponse",
)