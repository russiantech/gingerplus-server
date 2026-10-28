import uuid
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.redis import ResilientRedis as Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, Unauthorized
from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.session import get_db
from app.enums import Permission, UserType
from app.models import User

bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


async def _user_from_creds(db: AsyncSession, creds: HTTPAuthorizationCredentials | None) -> User | None:
    if not creds:
        return None
    try:
        payload = decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise Unauthorized("Invalid or expired token.", code="invalid_token")
    user = (await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))).scalar_one_or_none()
    if not user or not user.is_active:
        raise Unauthorized("Account unavailable.", code="invalid_token")
    return user


async def get_optional_user(db: DB, creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User | None:
    return await _user_from_creds(db, creds)


async def get_current_user(db: DB, creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    user = await _user_from_creds(db, creds)
    if not user:
        raise Unauthorized("Authentication required.", code="not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_permissions(*perms: Permission, any_of: bool = False) -> Callable:
    needed = {p.value for p in perms}

    async def checker(user: CurrentUser) -> User:
        have = set(user.permissions)
        if user.role_key == "super_admin":
            return user
        ok = bool(needed & have) if any_of else needed <= have
        if not ok:
            raise Forbidden("You do not have permission to perform this action.", code="missing_permission")
        return user

    return checker


async def require_staff(user: CurrentUser) -> User:
    if user.user_type != UserType.STAFF:
        raise Forbidden("Staff access only.", code="staff_only")
    return user


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
