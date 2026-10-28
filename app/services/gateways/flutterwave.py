"""Flutterwave (Standard / inline checkout). Server creates a payment link, browser opens the inline modal with the public
key + tx_ref, then the server verifies by reference. NOTE: written against Flutterwave's v3 API docs; test with your sandbox keys."""
import hmac
import logging
from decimal import Decimal

import httpx

from app.core.exceptions import PaymentError
from app.services.gateways.base import Gateway, InitResult, VerifyResult, WebhookEvent

log = logging.getLogger(__name__)
BASE_URL = "https://api.flutterwave.com"


class FlutterwaveGateway(Gateway):
    name = "flutterwave"

    async def _request(self, method: str, path: str, **kw) -> dict:
        if not self.creds.secret_key:
            raise PaymentError("Online payments are not configured yet.", code="gateway_not_configured")
        try:
            async with httpx.AsyncClient(base_url=self.creds.base_url or BASE_URL, timeout=20) as client:
                resp = await client.request(method, path, headers={"Authorization": f"Bearer {self.creds.secret_key}"}, **kw)
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.exception("flutterwave request failed")
            raise PaymentError("Payment gateway is unreachable. Please try again.", code="gateway_unreachable") from exc
        if resp.status_code >= 400 or body.get("status") != "success":
            raise PaymentError(body.get("message", "Payment gateway error"), code="gateway_error")
        return body.get("data") or {}

    async def initialize(self, payment, callback_url, metadata) -> InitResult:
        data = await self._request("POST", "/v3/payments", json={
            "tx_ref": payment.reference, "amount": str(payment.amount), "currency": payment.currency, "redirect_url": callback_url,
            "customer": {"email": payment.email, "name": payment.payer_name or payment.email, "phonenumber": payment.phone or ""},
            "customizations": {"title": "Southern Rose", "description": payment.description or "Payment"}, "meta": metadata,
        })
        return InitResult(authorization_url=data.get("link"), access_code=payment.reference, public_key=self.creds.public_key or None)

    @staticmethod
    def _result(data: dict) -> VerifyResult:
        st = (data.get("status") or "").lower()
        status = "success" if st in ("successful", "success") else "failed" if st in ("failed", "cancelled") else "pending"
        amount = Decimal(str(data["amount"])) if data.get("amount") is not None else None
        return VerifyResult(status=status, amount=amount, currency=data.get("currency", "NGN"), channel=data.get("payment_type"),
                            gateway_response=data.get("processor_response") or st, raw=data)

    async def verify(self, payment) -> VerifyResult:
        try:
            data = await self._request("GET", "/v3/transactions/verify_by_reference", params={"tx_ref": payment.reference})
        except PaymentError as exc:
            if exc.code == "gateway_error" and "no transaction" in exc.message.lower():
                return VerifyResult("pending", gateway_response="No transaction yet")
            raise
        return self._result(data)

    def verify_webhook(self, raw_body, headers) -> bool:
        sent = headers.get("verif-hash")
        secret = self.creds.webhook_secret or self.creds.secret_key
        return bool(sent and secret and hmac.compare_digest(sent, secret))

    def parse_webhook(self, body) -> WebhookEvent:
        data = body.get("data") or {}
        ref = data.get("tx_ref")
        if (body.get("event") or "").startswith("charge"):
            res = self._result(data)
            return WebhookEvent("success" if res.status == "success" else "failed" if res.status == "failed" else "ignore", ref, res)
        return WebhookEvent("ignore", ref)

    async def test(self) -> tuple[bool, str]:
        try:
            await self._request("GET", "/v3/banks/NG")
        except PaymentError as exc:
            return False, exc.message
        return True, "Connected to Flutterwave successfully."
