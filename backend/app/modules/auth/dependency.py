from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import supabase


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        return response.user

    except Exception as e:
        print(f"Supabase auth error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )