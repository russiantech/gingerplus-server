import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import PaymentError
from app.enums import PaymentMethod
from app.models import Order, User
from app.schemas.order import CheckoutRequest, CheckoutResponse
from app.services import order_service, payment_service
from app.services.settings_service import get_setting
from app.utils.text import whatsapp_link

log = logging.getLogger(__name__)


def order_whatsapp_url(order: Order, number: str) -> str:
    lines = "\n".join(f"- {i.quantity} × {i.product_name} ({i.variant_label})" for i in order.items)
    msg = (f"Hello Southern Rose, I just placed order {order.number}.\n{lines}\nTotal: ₦{order.total:,.0f}\n"
           f"Name: {order.customer_name}\nDelivery: {order.shipping_address.get('city', '')}, {order.delivery_state or ''}")
    return whatsapp_link(number, msg)


async def checkout(db: AsyncSession, data: CheckoutRequest, user: User | None) -> CheckoutResponse:
    order = await order_service.create_order(db, data, user)
    commerce = await get_setting(db, "commerce")
    contact = await get_setting(db, "contact")
    wa_number = (contact.get("whatsapp_numbers") or [settings.WHATSAPP_NUMBER])[0]
    auth_url = reference = None
    init = None
    wa_url = order_whatsapp_url(order, wa_number)
    next_step = "confirmation"

    if order.payment_method == PaymentMethod.PAYSTACK:
        try:
            payment = await payment_service.init_for_order(db, order, user)
            auth_url, reference, next_step = payment.authorization_url, payment.reference, "pay_online"
            init = payment_service.init_response(payment)
        except PaymentError:
            log.exception("gateway init failed for %s", order.number)
            next_step = "retry_payment"
    elif order.payment_method == PaymentMethod.WHATSAPP:
        next_step = "whatsapp"
    elif order.payment_method == PaymentMethod.BANK_TRANSFER:
        next_step = "bank_transfer"
    await order_service.notify_order_created(db, order)
    await db.refresh(order)
    from app.schemas.order import OrderOut
    return CheckoutResponse(order=OrderOut.model_validate(order), authorization_url=auth_url, payment_reference=reference, payment=init,
                            whatsapp_url=wa_url, next_step=next_step)
