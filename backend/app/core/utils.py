import uuid
from uuid import UUID
from typing import Annotated

from pydantic import BeforeValidator


def generate_uuid() -> str:
    """Generate a new UUID4 and return it as a lowercase hyphenated string."""
    return str(uuid.uuid4())


def _coerce_uuid(v):
    """Accept a UUID object or a UUID-format string; always return str."""
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, str):
        UUID(v)  # raises ValueError if the format is wrong
        return v
    raise ValueError(f"Expected a UUID string or UUID object, got {type(v).__name__}")


# Use as a Pydantic field type:  field: UUIDStr
# Accepts UUID objects and UUID-format strings; stores and serialises as str.
UUIDStr = Annotated[str, BeforeValidator(_coerce_uuid)]
