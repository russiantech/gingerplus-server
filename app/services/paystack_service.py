"""Thin async Paystack client (initialize / verify / refund) + webhook signature check."""
import hashlib
import hmac
import logging
from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.exceptions import PaymentError

log = logging.getLogger(__name__)


def is_mock_mode() -> bool:
    """Dev convenience: no Paystack key + non-production => simulated gateway."""
    return not settings.PAYSTACK_SECRET_KEY and not settings.is_production


def to_kobo(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature or not settings.PAYSTACK_SECRET_KEY:
        return False
    digest = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


async def _request(method: str, path: str, **kw) -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaymentError("Online payments are not configured yet.", code="gateway_not_configured")
    try:
        async with httpx.AsyncClient(base_url=settings.PAYSTACK_BASE_URL, timeout=20) as client:
            resp = await client.request(method, path, headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}, **kw)
        body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.exception("paystack request failed")
        raise PaymentError("Payment gateway is unreachable. Please try again.", code="gateway_unreachable") from exc
    if resp.status_code >= 400 or not body.get("status"):
        raise PaymentError(body.get("message", "Payment gateway error"), code="gateway_error")
    return body["data"]


async def initialize(*, email: str, amount: Decimal, reference: str, callback_url: str, metadata: dict) -> dict:
    if is_mock_mode():
        return {"authorization_url": f"{callback_url}?reference={reference}&mock=1", "access_code": "mock", "reference": reference}
    return await _request("POST", "/transaction/initialize", json={
        "email": email, "amount": to_kobo(amount), "reference": reference, "callback_url": callback_url,
        "currency": "NGN", "metadata": metadata,
    })


async def verify(reference: str) -> dict:
    return await _request("GET", f"/transaction/verify/{reference}")


async def refund(reference: str, amount: Decimal | None = None) -> dict:
    payload = {"transaction": reference}
    if amount is not None:
        payload["amount"] = to_kobo(amount)
    return await _request("POST", "/refund", json=payload)
