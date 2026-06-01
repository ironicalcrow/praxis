from pydantic import BaseModel, EmailStr
from typing import List, Optional

class ResumeSchema(BaseModel):
    name:str
    phone:str
    email:str
    location: Optional[str]= None
    skills: List[str]=[]
    education: List[str] = []
    experience: List[str] = []
    projects: List[str] = []
    certifications: List[str] = []
    years_of_experience: Optional[float] = None
    raw_text: Optional[str] = None