from fastapi import APIRouter, Depends
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse
)
from app.modules.auth.service import AuthService
from app.modules.auth.dependency import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    return AuthService.register_user(payload)


from fastapi import BackgroundTasks

def pre_warm_cache_task(user_id: str):
    import asyncio
    from app.modules.CV.db_service import fetch_resume_from_db
    from app.modules.CV.schemas import ResumeSchema
    from app.modules.jobs.services.job_suggestion import build_job_pool_from_queries
    
    async def pre_warm():
        try:
            resume_data = fetch_resume_from_db(user_id)
            if resume_data:
                candidate_resume = ResumeSchema(**resume_data)
                # This will automatically compute and cache for 24h
                await build_job_pool_from_queries(
                    queries=None,
                    candidate_resume=candidate_resume,
                    user_id=user_id
                )
        except Exception as e:
            print(f"Pre-warm failed: {e}")
            
    asyncio.run(pre_warm())

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, background_tasks: BackgroundTasks):
    auth_resp = AuthService.login_user(payload)
    if auth_resp.user and hasattr(auth_resp.user, "id"):
        background_tasks.add_task(pre_warm_cache_task, str(auth_resp.user.id))
    return auth_resp


@router.post("/logout")
def logout():
    return AuthService.logout_user()


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return AuthService.get_user_profile(current_user.id)