from app.core.session import Base

from app.modules.auth.models import User
from app.modules.CV.models import (
    Resume,
    ResumeSkill,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeCertification,
)
from app.modules.jobs.models import Job
from app.modules.application.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    ApplicationNote,
)
from app.modules.fit_score.models import JobFitScore


__all__ = [
    "Base",
    "User",
    "Resume",
    "ResumeSkill",
    "ResumeEducation",
    "ResumeExperience",
    "ResumeProject",
    "ResumeCertification",
    "Job",
    "Application",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "ApplicationNote",
    "JobFitScore",
]