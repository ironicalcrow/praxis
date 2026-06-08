
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
from app.modules.jobs.models import Job, JobQuery
from app.modules.application.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    ApplicationNote,
)
from app.modules.chat.models import ChatConversation, ChatSession, ChatMessage
from app.modules.roadmap.models import Roadmap, RoadmapPhase, RoadmapMilestone
from app.modules.goals.models import Goal
from app.modules.notifications.models import Notification
from app.modules.cover_letter.models import CoverLetter

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
    "JobQuery",
    "Application",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "ApplicationNote",
    "ChatConversation",
    "ChatSession",
    "ChatMessage",
    "Roadmap",
    "RoadmapPhase",
    "RoadmapMilestone",
    "Goal",
    "Notification",
    "CoverLetter",
]