"""Reversible encryption for secrets stored in the database (payment provider API keys).

Why encryption and not hashing: a hash cannot be turned back into the key, but the server must send the real secret key
to Paystack/Flutterwave. So secrets are encrypted at rest (Fernet = AES-128-CBC + HMAC) and decrypted only in memory,
server-side, at the moment a gateway call is made. A one-way SHA-256 fingerprint is kept next to it purely to show
admins *which* key is saved (and detect changes) without ever revealing it.
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

log = logging.getLogger(__name__)
PREFIX = "enc1:"


def _fernet() -> Fernet:
    raw = settings.ENCRYPTION_KEY or settings.SECRET_KEY
    key = raw.encode()
    try:  # a valid urlsafe-base64 32-byte Fernet key can be supplied directly
        if len(base64.urlsafe_b64decode(key)) == 32:
            return Fernet(key)
    except Exception:
        pass
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key).digest()))


def encrypt(plain: str) -> str:
    return PREFIX + _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """Returns None when empty or undecryptable (e.g. the encryption key was rotated) — callers treat that as 'not configured'."""
    if not token:
        return None
    if not token.startswith(PREFIX):
        return None
    try:
        return _fernet().decrypt(token[len(PREFIX):].encode()).decode()
    except (InvalidToken, ValueError):
        log.error("Could not decrypt a stored secret — ENCRYPTION_KEY/SECRET_KEY changed? Re-enter the credentials in Admin → Payment settings.")
        return None


def fingerprint(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()[:16]


def mask(plain: str | None) -> str | None:
    if not plain:
        return None
    if len(plain) <= 10:
        return "••••••••"
    head = plain.split("_")[0] + "_" + plain.split("_")[1] + "_" if plain.count("_") >= 2 else plain[:4]
    return f"{head}••••••••{plain[-4:]}"
