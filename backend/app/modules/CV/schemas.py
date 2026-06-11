from datetime import datetime
from uuid import UUID

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
    country: Optional[str] = None

    skills: List[str] = Field(default_factory=list)

    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    certifications: List[str] = Field(default_factory=list)

    years_of_experience: Optional[int] = None
    raw_text: Optional[str] = None


class ResumeResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    years_of_experience: Optional[int] = None
    raw_text: Optional[str] = None
    file_url: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UploadCVResponse(BaseModel):
    success: bool
    message: str
    resume_id: UUID
    file_url: Optional[str] = None
    data: ResumeSchema


class CVUploadRecord(BaseModel):
    id: str
    file_url: str
    original_filename: Optional[str] = None
    is_active: bool
    uploaded_at: datetime