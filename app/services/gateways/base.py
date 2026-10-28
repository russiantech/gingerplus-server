"""Gateway abstraction: every online provider implements the same small interface so the payment flow is provider-agnostic."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from app.models import Payment


@dataclass
class Credentials:
    provider: str
    secret_key: str = ""
    public_key: str = ""
    webhook_secret: str = ""
    mode: str = "test"
    source: str = "none"  # database | environment | none
    base_url: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class InitResult:
    authorization_url: str | None
    access_code: str | None
    public_key: str | None = None


@dataclass
class VerifyResult:
    status: str  # success | failed | pending
    amount: Decimal | None = None  # major units (₦)
    currency: str = "NGN"
    channel: str | None = None
    gateway_response: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def payload(self, provider: str) -> dict:
        return {"provider": provider, "channel": self.channel, "gateway_response": self.gateway_response, "raw": self.raw}


@dataclass
class WebhookEvent:
    kind: str  # success | failed | refund | ignore
    reference: str | None = None
    result: VerifyResult | None = None


class Gateway:
    name = "base"

    def __init__(self, creds: Credentials) -> None:
        self.creds = creds

    async def initialize(self, payment: "Payment", callback_url: str, metadata: dict) -> InitResult:  # pragma: no cover
        raise NotImplementedError

    async def verify(self, payment: "Payment") -> VerifyResult:  # pragma: no cover
        raise NotImplementedError

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> bool:  # pragma: no cover
        raise NotImplementedError

    def parse_webhook(self, body: dict) -> WebhookEvent:  # pragma: no cover
        raise NotImplementedError

    async def test(self) -> tuple[bool, str]:  # pragma: no cover
        raise NotImplementedError
