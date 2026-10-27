"""Registration (Redis-staged until email verified), login, refresh, password reset."""
import json
import uuid
from datetime import datetime, timezone

import jwt
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import Conflict, Forbidden, NotFound, TooManyRequests, Unauthorized, AppError
from app.core.security import (constant_time_eq, create_access_token, create_refresh_token, decode_token,
                               generate_numeric_code, hash_code, hash_password, verify_password)
from app.enums import UserType
from app.models import NewsletterSubscriber, Order, Role, User
from app.schemas.auth import RegisterRequest, TokenPair
from app.services.email_service import send_email
from app.utils.text import normalize_email, normalize_phone

PENDING = "reg:pending:{}"
COOLDOWN = "reg:cooldown:{}"
RESET = "pwreset:{}"
REFRESH = "rt:{}:{}"


async def start_registration(db: AsyncSession, redis: Redis, data: RegisterRequest) -> dict:
    email = normalize_email(data.email)
    if (await db.execute(select(User.id).where(User.email == email))).scalar_one_or_none():
        raise Conflict("An account with this email already exists. Please sign in.", code="email_taken")
    if await redis.exists(COOLDOWN.format(email)):
        ttl = await redis.ttl(COOLDOWN.format(email))
        raise TooManyRequests(f"Please wait {max(ttl, 1)}s before requesting another code.", extra={"retry_after": ttl})

    code = generate_numeric_code(6)
    salt = uuid.uuid4().hex
    payload = {
        "email": email, "first_name": data.first_name.strip(), "last_name": data.last_name.strip(),
        "phone": normalize_phone(data.phone), "marketing_opt_in": data.marketing_opt_in,
        "password_hash": hash_password(data.password), "salt": salt, "code_hash": hash_code(code, salt), "attempts": 0,
    }
    await redis.set(PENDING.format(email), json.dumps(payload), ex=settings.VERIFICATION_CODE_TTL_SECONDS)
    await redis.set(COOLDOWN.format(email), "1", ex=settings.VERIFICATION_RESEND_COOLDOWN_SECONDS)
    await send_email(db, email, "Your Southern Rose verification code", "verification.html", log_to_inbox=False,
                     first_name=payload["first_name"], code=code, minutes=settings.VERIFICATION_CODE_TTL_SECONDS // 60,
                     body=f"Your verification code is {code}")
    return {"email": email, "expires_in": settings.VERIFICATION_CODE_TTL_SECONDS, "resend_in": settings.VERIFICATION_RESEND_COOLDOWN_SECONDS}


async def resend_code(db: AsyncSession, redis: Redis, email: str) -> dict:
    email = normalize_email(email)
    raw = await redis.get(PENDING.format(email))
    if not raw:
        raise NotFound("No pending registration for this email. Please register again.", code="no_pending_registration")
    if await redis.exists(COOLDOWN.format(email)):
        ttl = await redis.ttl(COOLDOWN.format(email))
        raise TooManyRequests(f"Please wait {max(ttl, 1)}s before requesting another code.", extra={"retry_after": ttl})
    payload = json.loads(raw)
    code = generate_numeric_code(6)
    payload.update(code_hash=hash_code(code, payload["salt"]), attempts=0)
    await redis.set(PENDING.format(email), json.dumps(payload), ex=settings.VERIFICATION_CODE_TTL_SECONDS)
    await redis.set(COOLDOWN.format(email), "1", ex=settings.VERIFICATION_RESEND_COOLDOWN_SECONDS)
    await send_email(db, email, "Your Southern Rose verification code", "verification.html", log_to_inbox=False,
                     first_name=payload["first_name"], code=code, minutes=settings.VERIFICATION_CODE_TTL_SECONDS // 60,
                     body=f"Your verification code is {code}")
    return {"email": email, "expires_in": settings.VERIFICATION_CODE_TTL_SECONDS, "resend_in": settings.VERIFICATION_RESEND_COOLDOWN_SECONDS}


async def _customer_role(db: AsyncSession) -> Role | None:
    return (await db.execute(select(Role).where(Role.key == "customer"))).scalar_one_or_none()


async def verify_registration(db: AsyncSession, redis: Redis, email: str, code: str) -> User:
    email = normalize_email(email)
    key = PENDING.format(email)
    raw = await redis.get(key)
    if not raw:
        raise NotFound("Your code has expired. Please register again.", code="code_expired")
    payload = json.loads(raw)
    if payload["attempts"] >= settings.VERIFICATION_MAX_ATTEMPTS:
        await redis.delete(key)
        raise TooManyRequests("Too many incorrect attempts. Please register again.", code="too_many_attempts")
    if not constant_time_eq(hash_code(code, payload["salt"]), payload["code_hash"]):
        payload["attempts"] += 1
        ttl = await redis.ttl(key)
        await redis.set(key, json.dumps(payload), ex=max(ttl, 1))
        left = settings.VERIFICATION_MAX_ATTEMPTS - payload["attempts"]
        raise AppError(f"Incorrect code. {left} attempt(s) left.", code="invalid_code")

    if (await db.execute(select(User.id).where(User.email == email))).scalar_one_or_none():
        await redis.delete(key)
        raise Conflict("Account already exists.", code="email_taken")

    role = await _customer_role(db)
    user = User(
        email=email, password_hash=payload["password_hash"], first_name=payload["first_name"], last_name=payload["last_name"],
        phone=payload["phone"], marketing_opt_in=payload["marketing_opt_in"], user_type=UserType.CUSTOMER,
        role_id=role.id if role else None, email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    # attach earlier guest orders placed with this email
    await db.execute(update(Order).where(Order.customer_email == email, Order.user_id.is_(None)).values(user_id=user.id))
    if user.marketing_opt_in:
        existing = (await db.execute(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))).scalar_one_or_none()
        if not existing:
            db.add(NewsletterSubscriber(email=email, name=user.first_name, unsubscribe_token=uuid.uuid4().hex))
    await redis.delete(key, COOLDOWN.format(email))
    await db.refresh(user, ["role"])
    await send_email(db, email, "Welcome to Southern Rose", "welcome.html", first_name=user.first_name, is_system=True)
    return user


async def issue_tokens(redis: Redis, user: User) -> TokenPair:
    access = create_access_token(user.id)
    refresh, jti = create_refresh_token(user.id)
    await redis.set(REFRESH.format(user.id, jti), "1", ex=settings.REFRESH_TOKEN_DAYS * 86400)
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=settings.ACCESS_TOKEN_MINUTES * 60)


async def login(db: AsyncSession, redis: Redis, email: str, password: str) -> tuple[User, TokenPair]:
    email = normalize_email(email)
    fail_key = f"login:fail:{email}"
    if int(await redis.get(fail_key) or 0) >= 10:
        raise TooManyRequests("Too many failed attempts. Try again in 15 minutes.")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        await redis.incr(fail_key)
        await redis.expire(fail_key, 900)
        raise Unauthorized("Invalid email or password.", code="invalid_credentials")
    if not user.is_active:
        raise Forbidden("This account has been deactivated.", code="account_disabled")
    await redis.delete(fail_key)
    user.last_login_at = datetime.now(timezone.utc)
    return user, await issue_tokens(redis, user)


async def refresh(db: AsyncSession, redis: Redis, refresh_token: str) -> tuple[User, TokenPair]:
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.PyJWTError:
        raise Unauthorized("Invalid or expired refresh token.", code="invalid_token")
    key = REFRESH.format(payload["sub"], payload["jti"])
    if not await redis.get(key):
        raise Unauthorized("Session expired. Please sign in again.", code="session_revoked")
    await redis.delete(key)  # rotate
    user = (await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))).scalar_one_or_none()
    if not user or not user.is_active:
        raise Unauthorized("Account unavailable.")
    return user, await issue_tokens(redis, user)


async def logout(redis: Redis, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token, "refresh")
        await redis.delete(REFRESH.format(payload["sub"], payload["jti"]))
    except jwt.PyJWTError:
        pass


async def forgot_password(db: AsyncSession, redis: Redis, email: str) -> None:
    email = normalize_email(email)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or await redis.exists(f"pwreset:cd:{email}"):
        return  # never reveal whether the account exists
    code = generate_numeric_code(6)
    salt = uuid.uuid4().hex
    await redis.set(RESET.format(email), json.dumps({"salt": salt, "code_hash": hash_code(code, salt), "attempts": 0}), ex=settings.PASSWORD_RESET_TTL_SECONDS)
    await redis.set(f"pwreset:cd:{email}", "1", ex=settings.VERIFICATION_RESEND_COOLDOWN_SECONDS)
    await send_email(db, email, "Reset your Southern Rose password", "password_reset.html", log_to_inbox=False,
                     first_name=user.first_name, code=code, minutes=settings.PASSWORD_RESET_TTL_SECONDS // 60, body=f"Your reset code is {code}")


async def reset_password(db: AsyncSession, redis: Redis, email: str, code: str, new_password: str) -> None:
    email = normalize_email(email)
    raw = await redis.get(RESET.format(email))
    if not raw:
        raise AppError("Reset code expired or invalid.", code="code_expired")
    payload = json.loads(raw)
    if payload["attempts"] >= settings.VERIFICATION_MAX_ATTEMPTS:
        await redis.delete(RESET.format(email))
        raise TooManyRequests("Too many attempts. Request a new code.")
    if not constant_time_eq(hash_code(code, payload["salt"]), payload["code_hash"]):
        payload["attempts"] += 1
        await redis.set(RESET.format(email), json.dumps(payload), ex=max(await redis.ttl(RESET.format(email)), 1))
        raise AppError("Incorrect code.", code="invalid_code")
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise NotFound("Account not found")
    user.password_hash = hash_password(new_password)
    await redis.delete(RESET.format(email))
