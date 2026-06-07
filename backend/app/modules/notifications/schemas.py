from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Any] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
