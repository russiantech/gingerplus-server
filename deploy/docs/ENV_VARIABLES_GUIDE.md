# Environment Variables — api.gingerplus.ng

Secrets live in `/home/gingerpl/api.gingerplus.ng/.env` (never in git, `chmod 600`). The app reads it on start; after any change run `bash deploy/control.sh restart`.

## Minimum production `.env`

```ini
ENVIRONMENT=production
SITE_URL=https://gingerplus.ng
API_URL=https://api.gingerplus.ng
CORS_ORIGINS=["https://gingerplus.ng","https://www.gingerplus.ng"]

# cPanel → PostgreSQL Databases (create DB + user, add user to DB with ALL privileges)
DATABASE_URL=postgresql+asyncpg://gingerpl_user:PASSWORD@localhost:5432/gingerpl_db
# cPanel usually has no Redis. Leave empty → in-memory fallback, which is per-process: keep WORKERS="1" in deploy/config.env.
# With a managed Redis URL (rediss://...) you can raise WORKERS to 2-4 (shared sessions, sign-up codes, rate limits).
REDIS_URL=

SECRET_KEY=            # openssl rand -hex 32
ENCRYPTION_KEY=        # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

FIRST_SUPERUSER_EMAIL=you@gingerplus.ng
FIRST_SUPERUSER_PASSWORD=choose-a-strong-one

EMAIL_ENABLED=true
SMTP_HOST=mail.gingerplus.ng
SMTP_PORT=587
SMTP_USER=no-reply@gingerplus.ng
SMTP_PASSWORD=
EMAIL_FROM=Southern Rose <no-reply@gingerplus.ng>
ADMIN_NOTIFY_EMAIL=southernrose.enueshike@gmail.com

STORAGE_BACKEND=local   # uploads saved in app/static/uploads and served at /static/ (keep it backed up)
AUTO_SEED=false
```

Paystack/Flutterwave keys are entered in **Admin → Payment settings** (stored encrypted). `.env` keys are only a fallback.

## Rules

- Rotating `SECRET_KEY` logs everyone out; if `ENCRYPTION_KEY` is empty, it also forces re-entering gateway keys. Set `ENCRYPTION_KEY` once and keep it.
- `CORS_ORIGINS` must be a JSON list that contains the exact storefront origin.
- Verify: `curl https://api.gingerplus.ng/api/v1/catalog/products`.
