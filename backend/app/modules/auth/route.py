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


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    return AuthService.login_user(payload)


@router.post("/logout")
def logout():
    return AuthService.logout_user()


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return AuthService.get_user_profile(current_user.id)