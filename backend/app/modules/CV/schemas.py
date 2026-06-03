from pydantic import BaseModel
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

    skills: List[str] = []

    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []

    certifications: List[str] = []

    years_of_experience: Optional[int] = None
    raw_text: Optional[str] = None