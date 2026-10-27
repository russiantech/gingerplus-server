import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def _encode(payload: dict, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**payload, "iat": now, "exp": now + expires}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _encode({"sub": str(user_id), "type": "access"}, timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    jti = uuid.uuid4().hex
    token = _encode({"sub": str(user_id), "type": "refresh", "jti": jti}, timedelta(days=settings.REFRESH_TOKEN_DAYS))
    return token, jti


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def generate_numeric_code(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_code(code: str, salt: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{salt}:{code}".encode(), hashlib.sha256).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
