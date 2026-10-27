from fastapi import APIRouter

from app.api.deps import DB, CurrentUser, RedisDep
from app.schemas.auth import (AuthResponse, ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, RefreshRequest, RegisterRequest,
                              RegisterResponse, ResendCodeRequest, ResetPasswordRequest, UserOut, VerifyEmailRequest)
from app.schemas.common import Message
from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=202)
async def register(data: RegisterRequest, db: DB, redis: RedisDep):
    """Stage the account in Redis and email a 6-digit code. Nothing is written to Postgres until verified."""
    return await auth_service.start_registration(db, redis, data)


@router.post("/resend-code", response_model=RegisterResponse, status_code=202)
async def resend(data: ResendCodeRequest, db: DB, redis: RedisDep):
    return await auth_service.resend_code(db, redis, data.email)


@router.post("/verify-email", response_model=AuthResponse, status_code=201)
async def verify_email(data: VerifyEmailRequest, db: DB, redis: RedisDep):
    user = await auth_service.verify_registration(db, redis, data.email, data.code)
    tokens = await auth_service.issue_tokens(redis, user)
    return AuthResponse(tokens=tokens, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: DB, redis: RedisDep):
    user, tokens = await auth_service.login(db, redis, data.email, data.password)
    return AuthResponse(tokens=tokens, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh(data: RefreshRequest, db: DB, redis: RedisDep):
    user, tokens = await auth_service.refresh(db, redis, data.refresh_token)
    return AuthResponse(tokens=tokens, user=UserOut.model_validate(user))


@router.post("/logout", response_model=Message)
async def logout(data: RefreshRequest, redis: RedisDep):
    await auth_service.logout(redis, data.refresh_token)
    return Message(detail="Signed out")


@router.post("/forgot-password", response_model=Message, status_code=202)
async def forgot(data: ForgotPasswordRequest, db: DB, redis: RedisDep):
    await auth_service.forgot_password(db, redis, data.email)
    return Message(detail="If an account exists, a reset code has been sent.")


@router.post("/reset-password", response_model=Message)
async def reset(data: ResetPasswordRequest, db: DB, redis: RedisDep):
    await auth_service.reset_password(db, redis, data.email, data.code, data.new_password)
    return Message(detail="Password updated. You can sign in now.")


@router.post("/change-password", response_model=Message)
async def change_password(data: ChangePasswordRequest, user: CurrentUser):
    if not verify_password(data.current_password, user.password_hash):
        raise AppError("Current password is incorrect.", code="invalid_password")
    user.password_hash = hash_password(data.new_password)
    return Message(detail="Password changed.")
