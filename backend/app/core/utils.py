import uuid


def generate_uuid() -> str:
    """Generate a new UUID4 and return it as a lowercase hyphenated string."""
    return str(uuid.uuid4())
