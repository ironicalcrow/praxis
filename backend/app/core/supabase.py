from supabase import create_client, Client
from app.core.config import settings
from app.core.session import get_db, get_session

# Supabase REST API clients
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)