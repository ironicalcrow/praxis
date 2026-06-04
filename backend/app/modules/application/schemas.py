from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class ApplicationCreation(BaseModel):
    user_id: str
    job: Dict[str, Any]

class ApplicationCreationManual(BaseModel):
    user_id: str
    job_title: str
    company: str
    location: Optional[str] = None
    apply_url: Optional[str] = None
    source: Optional[str] = "manual"
    salary: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    user_id: str
    status: str
class ApplicationNoteRequest(BaseModel):
    user_id:str
    content:str
class ApplicationNoteRespone(BaseModel):
    id: str
    application_id: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationStatusHistoryResponse(BaseModel):
    id: str
    old_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: str
    user_id: str
    job_id: Optional[str] = None

    job_title: str
    company: str
    location: Optional[str] = None
    apply_url: Optional[str] = None
    source: Optional[str] = None
    salary: Optional[str] = None

    status: str
    applied_at: datetime
    last_status_changed_at: datetime

    is_archived: bool

    created_at: datetime
    updated_at: Optional[datetime] = None

    notes: List[ApplicationNoteRespone] = []
    status_history: List[ApplicationStatusHistoryResponse] = []

    class Config:
        from_attributes = True

class DeleteApplicationResponse(BaseModel):
    deleted: bool
    application_id: str