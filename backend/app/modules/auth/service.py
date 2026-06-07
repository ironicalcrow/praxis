from fastapi import HTTPException

from app.core.supabase import supabase
from app.core.session import get_session
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest, LoginRequest, AuthResponse


class AuthService:

    @staticmethod
    def register_user(payload: RegisterRequest) -> AuthResponse:
        db = get_session()

        try:
            existing_user = (
                db.query(User)
                .filter(User.username == payload.username)
                .first()
            )

            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="Username already exists",
                )

            existing_user = (
                db.query(User)
                .filter(User.email == payload.email)
                .first()
            )

            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="Email already exists",
                )

            auth_response = supabase.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "name": payload.name,
                        "username": payload.username,
                    }
                },
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=400,
                    detail="Registration failed",
                )

            new_user = User(
                id=str(auth_response.user.id),
                name=payload.name,
                username=payload.username,
                email=payload.email,
            )

            db.add(new_user)
            db.commit()

            session = auth_response.session

            if not session:
                raise HTTPException(
                    status_code=201,
                    detail="User registered. Please verify email before login.",
                )

            return AuthResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
            )

        except HTTPException:
            db.rollback()
            raise

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        finally:
            db.close()

    @staticmethod
    def login_user(payload: LoginRequest) -> AuthResponse:
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password,
            })

            if not auth_response.session:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password",
                )

            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=auth_response.user
            )

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

    @staticmethod
    def logout_user():
        try:
            supabase.auth.sign_out()

            return {
                "message": "Logged out successfully",
            }

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

    @staticmethod
    def get_user_profile(user_id: str):
        db = get_session()

        try:
            user = (
                db.query(User)
                .filter(User.id == str(user_id))
                .first()
            )

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="User profile not found",
                )

            return {
                "id": str(user.id),
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        finally:
            db.close()