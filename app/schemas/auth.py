import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.enums import UserType
from app.schemas.common import ORM


def _strong(pw: str) -> str:
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise ValueError("Password must be at least 8 characters and include a letter and a number")
    return pw


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    marketing_opt_in: bool = False

    _pw = field_validator("password")(_strong)


class RegisterResponse(BaseModel):
    email: EmailStr
    expires_in: int
    resend_in: int
    detail: str = "Verification code sent"


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str
    _pw = field_validator("new_password")(_strong)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    _pw = field_validator("new_password")(_strong)


class RoleOut(ORM):
    id: uuid.UUID
    key: str
    name: str
    description: str
    permissions: list[str]
    is_system: bool


class UserOut(ORM):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    phone: str | None
    avatar_url: str | None
    user_type: UserType
    role_key: str | None
    permissions: list[str]
    is_active: bool
    email_verified_at: datetime | None
    marketing_opt_in: bool
    linked_store_id: uuid.UUID | None
    created_at: datetime


class AuthResponse(BaseModel):
    tokens: TokenPair
    user: UserOut


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    marketing_opt_in: bool | None = None
    avatar_url: str | None = None
