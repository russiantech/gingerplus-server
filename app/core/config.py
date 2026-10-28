"""Application configuration (12-factor, env driven)."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Southern Rose API"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    SITE_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8000"
    CORS_ORIGINS: List[str] = ["", "http://localhost:5173", "http://localhost:3000"]

    # Database / cache
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/southern_rose"
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_NULL_POOL: bool = False  # disable connection pooling for serverless deployments (e.g. Vercel)

    # Auth
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7

    # Email verification
    VERIFICATION_CODE_TTL_SECONDS: int = 15 * 60
    VERIFICATION_MAX_ATTEMPTS: int = 5
    VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    PASSWORD_RESET_TTL_SECONDS: int = 30 * 60

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False
    SMTP_STARTTLS: bool = False
    EMAIL_FROM: str = "Southern Rose <no-reply@southernrose.ng>"
    EMAIL_ENABLED: bool = True  # when False, emails are logged/stored only
    ADMIN_NOTIFY_EMAIL: str = "southernrose.enueshike@gmail.com"

    # Paystack
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    PAYSTACK_CALLBACK_PATH: str = "/payment/callback"

    # Business defaults (overridable by admin through site settings)
    ONLINE_PAYMENT_MAX_PACKS: int = 5  # orders with fewer packs go straight to the gateway
    WHATSAPP_NUMBER: str = "2348027724193"
    DEFAULT_DELIVERY_FEE: int = 3500

    # Seed super admin
    AUTO_SEED: bool = True
    FIRST_SUPERUSER_EMAIL: str = "admin@southernrose.ng"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"

    # Uploads
    UPLOAD_DIR: str = "app/static/uploads"
    MAX_UPLOAD_MB: int = 8

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
