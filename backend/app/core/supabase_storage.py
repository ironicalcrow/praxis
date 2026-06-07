from supabase import create_client
from app.core.config import settings


def _client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def upload_cv(file_bytes: bytes, storage_path: str) -> str:
    """Upload bytes to the CV bucket. Returns the public URL."""
    c = _client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    c.storage.from_(bucket).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    return c.storage.from_(bucket).get_public_url(storage_path)


def download_cv(storage_path: str) -> bytes:
    """Download file bytes from the CV bucket."""
    c = _client()
    return c.storage.from_(settings.SUPABASE_STORAGE_BUCKET).download(storage_path)
