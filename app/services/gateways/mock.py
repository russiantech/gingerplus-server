"""Development-only simulated gateway. Active only when no real credentials exist anywhere and ENVIRONMENT != production."""
from app.services.gateways.base import Credentials, Gateway, InitResult, VerifyResult, WebhookEvent


class MockGateway(Gateway):
    name = "mock"

    def __init__(self, creds: Credentials | None = None) -> None:
        super().__init__(creds or Credentials(provider="mock", source="mock"))

    async def initialize(self, payment, callback_url, metadata) -> InitResult:
        return InitResult(authorization_url=f"{callback_url}?reference={payment.reference}&mock=1", access_code="mock", public_key=None)

    async def verify(self, payment) -> VerifyResult:
        outcome = (payment.gateway_payload or {}).get("mock_outcome")
        if outcome == "success":
            return VerifyResult("success", amount=payment.amount, channel="mock", gateway_response="Mock payment (dev)", raw={"mock": True})
        if outcome == "failed":
            return VerifyResult("failed", gateway_response="Mock payment declined", raw={"mock": True})
        return VerifyResult("pending", gateway_response="Awaiting mock payment")

    def verify_webhook(self, raw_body, headers) -> bool:
        return False

    def parse_webhook(self, body) -> WebhookEvent:
        return WebhookEvent("ignore")

    async def test(self) -> tuple[bool, str]:
        return True, "Mock gateway (development only)."
