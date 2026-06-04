from pydantic import BaseModel, Field
from typing import List, Optional


class Education(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None


class Experience(BaseModel):
    role: Optional[str] = None
    organization: Optional[str] = None
    description: Optional[str] = None


class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technology: Optional[str] = None


class ResumeSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    skills: List[str] = Field(default_factory=list)

    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    certifications: List[str] = Field(default_factory=list)

    years_of_experience: Optional[int] = None
    raw_text: Optional[str] = None


class ResumeResponse(BaseModel):
    id: str
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    raw_text: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UploadCVResponse(BaseModel):
    success: bool
    message: str
    resume_id: str
    data: ResumeSchema