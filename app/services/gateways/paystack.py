"""Paystack: initialize → (popup in the browser via access_code) → verify / webhook."""
import hashlib
import hmac
import logging
from decimal import Decimal

import httpx

from app.core.exceptions import PaymentError
from app.services.gateways.base import Gateway, InitResult, VerifyResult, WebhookEvent

log = logging.getLogger(__name__)
BASE_URL = "https://api.paystack.co"


def to_kobo(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


class PaystackGateway(Gateway):
    name = "paystack"

    async def _request(self, method: str, path: str, **kw) -> dict:
        if not self.creds.secret_key:
            raise PaymentError("Online payments are not configured yet.", code="gateway_not_configured")
        try:
            async with httpx.AsyncClient(base_url=self.creds.base_url or BASE_URL, timeout=20) as client:
                resp = await client.request(method, path, headers={"Authorization": f"Bearer {self.creds.secret_key}"}, **kw)
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.exception("paystack request failed")
            raise PaymentError("Payment gateway is unreachable. Please try again.", code="gateway_unreachable") from exc
        if resp.status_code >= 400 or not body.get("status"):
            raise PaymentError(body.get("message", "Payment gateway error"), code="gateway_error")
        return body["data"]

    async def initialize(self, payment, callback_url, metadata) -> InitResult:
        data = await self._request("POST", "/transaction/initialize", json={
            "email": payment.email, "amount": to_kobo(payment.amount), "reference": payment.reference, "callback_url": callback_url,
            "currency": payment.currency, "metadata": metadata,
        })
        return InitResult(authorization_url=data.get("authorization_url"), access_code=data.get("access_code"), public_key=self.creds.public_key or None)

    @staticmethod
    def _result(data: dict) -> VerifyResult:
        st = data.get("status")
        status = "success" if st == "success" else "failed" if st in ("failed", "abandoned", "reversed") else "pending"
        amount = Decimal(int(data["amount"])) / 100 if data.get("amount") is not None else None
        return VerifyResult(status=status, amount=amount, currency=data.get("currency", "NGN"), channel=data.get("channel"),
                            gateway_response=data.get("gateway_response") or st, raw=data)

    async def verify(self, payment) -> VerifyResult:
        return self._result(await self._request("GET", f"/transaction/verify/{payment.reference}"))

    def verify_webhook(self, raw_body, headers) -> bool:
        sig = headers.get("x-paystack-signature")
        if not sig or not self.creds.secret_key:
            return False
        digest = hmac.new(self.creds.secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(digest, sig)

    def parse_webhook(self, body) -> WebhookEvent:
        name, data = body.get("event"), body.get("data") or {}
        ref = data.get("reference")
        if name == "charge.success":
            return WebhookEvent("success", ref, self._result(data))
        if name == "charge.failed":
            return WebhookEvent("failed", ref, VerifyResult("failed", gateway_response=data.get("gateway_response"), raw=data))
        if name == "refund.processed":
            return WebhookEvent("refund", data.get("transaction_reference") or ref)
        return WebhookEvent("ignore", ref)

    async def test(self) -> tuple[bool, str]:
        try:
            await self._request("GET", "/transaction", params={"perPage": 1})
        except PaymentError as exc:
            return False, exc.message
        return True, "Connected to Paystack successfully."
