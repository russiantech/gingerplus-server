import json
import logging

from fastapi import APIRouter, Header, Request

from app.api.deps import DB, OptionalUser
from app.core.exceptions import Unauthorized
from app.schemas.common import Message
from app.schemas.payment import DirectPaymentRequest, InitPaymentResponse, PaymentPublicStatus
from app.services import order_service, payment_service, paystack_service

router = APIRouter(prefix="/payments", tags=["payments"])
log = logging.getLogger(__name__)


@router.post("/direct", response_model=InitPaymentResponse, status_code=201)
async def direct_payment(data: DirectPaymentRequest, db: DB, user: OptionalUser):
    """Public 'Pay now' page: pay any agreed amount, optionally against an existing order number."""
    p = await payment_service.init_direct(db, data, user)
    return InitPaymentResponse(reference=p.reference, authorization_url=p.authorization_url, access_code=p.access_code, amount=float(p.amount))


@router.get("/verify/{reference}", response_model=PaymentPublicStatus)
async def verify(reference: str, db: DB):
    """Called by the callback page. Verifies with Paystack and settles (idempotent)."""
    p = await payment_service.verify_reference(db, reference)
    number = None
    if p.order_id:
        number = (await order_service.get_order(db, p.order_id)).number
    return PaymentPublicStatus(reference=p.reference, status=p.status, amount=float(p.amount), order_number=number, paid_at=p.paid_at)


@router.post("/webhook/paystack", response_model=Message)
async def paystack_webhook(request: Request, db: DB, x_paystack_signature: str | None = Header(default=None)):
    raw = await request.body()
    if not paystack_service.verify_signature(raw, x_paystack_signature):
        raise Unauthorized("Invalid signature", code="invalid_signature")
    await payment_service.handle_webhook(db, json.loads(raw))
    return Message(detail="ok")
