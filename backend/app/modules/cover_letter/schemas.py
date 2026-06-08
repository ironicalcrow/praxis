from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CoverLetterGenerate(BaseModel):
    job_id: str
    tone: str = "professional"  # "professional" | "enthusiastic" | "concise"


class CoverLetterUpdate(BaseModel):
    content: str


class CoverLetterOut(BaseModel):
    id: str
    job_id: Optional[str] = None
    content: str
    tone: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
