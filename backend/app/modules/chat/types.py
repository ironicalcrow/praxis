from typing import Any, Literal

from pydantic import BaseModel


class ToolExecutionResult(BaseModel):
    status: Literal["handled", "unsupported", "failed", "confirmation_required"]
    message: str
    payload_type: str | None = None
    payload: Any | None = None
    should_notify: bool = False
    notification_type: str | None = None
    notification_title: str | None = None
    notification_message: str | None = None
    notification_data: dict | None = None
