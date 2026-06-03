from fastapi import HTTPException
from app.core.supabase import supabase, supabase_admin
from app.modules.auth.schemas import RegisterRequest, LoginRequest, AuthResponse


class AuthService:

    @staticmethod
    def register_user(payload: RegisterRequest) -> AuthResponse:
        try:
            existing_username = (
                supabase_admin
                .table("users")
                .select("id")
                .eq("username", payload.username)
                .execute()
            )

            if existing_username.data:
                raise HTTPException(
                    status_code=400,
                    detail="Username already exists"
                )

            auth_response = supabase.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "name": payload.name,
                        "username": payload.username
                    }
                }
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=400,
                    detail="Registration failed"
                )

            user_id = auth_response.user.id

            supabase_admin.table("users").insert({
                "id": user_id,
                "name": payload.name,
                "username": payload.username,
                "email": payload.email,
            }).execute()

            session = auth_response.session

            if not session:
                raise HTTPException(
                    status_code=201,
                    detail="User registered. Please verify email before login."
                )

            return AuthResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token
            )

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    def login_user(payload: LoginRequest) -> AuthResponse:
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password
            })

            if not auth_response.session:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )

            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token
            )

        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

    @staticmethod
    def logout_user():
        try:
            supabase.auth.sign_out()
            return {"message": "Logged out successfully"}

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    def get_user_profile(user_id: str):
        try:
            user_data = (
                supabase_admin
                .table("users")
                .select("id, name, username, email")
                .eq("id", user_id)
                .single()
                .execute()
            )

            if not user_data.data:
                raise HTTPException(
                    status_code=404,
                    detail="User profile not found"
                )

            return user_data.data

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))