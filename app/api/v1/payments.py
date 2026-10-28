import json
import logging

from fastapi import APIRouter, Request

from app.api.deps import DB, OptionalUser
from app.core.exceptions import NotFound, Unauthorized
from app.schemas.common import Message
from app.schemas.payment import (DirectPaymentRequest, InitPaymentResponse, MockCompleteRequest, PaymentConfigOut, PaymentPublicStatus,
                                 VerifyRequest)
from app.services import order_service, payment_service, provider_service

router = APIRouter(prefix="/payments", tags=["payments"])
log = logging.getLogger(__name__)


async def _status(db, p) -> PaymentPublicStatus:
    number = (await order_service.get_order(db, p.order_id)).number if p.order_id else None
    return PaymentPublicStatus(reference=p.reference, status=p.status, amount=float(p.amount), order_number=number, paid_at=p.paid_at, message=p.gateway_response)


@router.get("/config", response_model=PaymentConfigOut)
async def payment_config(db: DB):
    """Public: is online payment available (and via which provider), plus bank-transfer details if the admin enabled them."""
    return await provider_service.public_config(db)


@router.post("/direct", response_model=InitPaymentResponse, status_code=201)
async def direct_payment(data: DirectPaymentRequest, db: DB, user: OptionalUser):
    """Public 'Pay now' page: pay any agreed amount, optionally against an existing order number."""
    return payment_service.init_response(await payment_service.init_direct(db, data, user))


@router.post("/verify", response_model=PaymentPublicStatus)
async def verify_post(data: VerifyRequest, db: DB):
    """Called by the browser right after the popup reports success: the backend asks the provider and settles (idempotent)."""
    return await _status(db, await payment_service.verify_reference(db, data.reference))


@router.get("/verify/{reference}", response_model=PaymentPublicStatus)
async def verify(reference: str, db: DB):
    """Same as POST /verify — used by the fallback callback page."""
    return await _status(db, await payment_service.verify_reference(db, reference))


@router.post("/mock/complete", response_model=Message)
async def mock_complete(data: MockCompleteRequest, db: DB):
    """Development only: lets the in-app test popup 'pay'. 404 in production."""
    await payment_service.mock_complete(db, data.reference, data.outcome)
    return Message(detail="ok")


@router.post("/webhook/{provider}", response_model=Message)
async def webhook(provider: str, request: Request, db: DB):
    """Provider → backend notifications. The signature is checked with the credentials in use (database first, then env)."""
    if provider not in provider_service.ONLINE:
        raise NotFound("Unknown provider.")
    raw = await request.body()
    try:
        gateway = await provider_service.gateway_for(db, provider)
    except Exception:
        raise Unauthorized("Provider not configured", code="provider_unconfigured")
    if not gateway.verify_webhook(raw, {k.lower(): v for k, v in request.headers.items()}):
        raise Unauthorized("Invalid signature", code="invalid_signature")
    try:
        body = json.loads(raw)
    except ValueError:
        return Message(detail="ignored")
    await payment_service.handle_webhook(db, provider, body)
    return Message(detail="ok")
