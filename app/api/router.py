from fastapi import APIRouter

from app.api.v1 import analytics, auth, catalog, checkout, contact, content, me, payments, stores
from app.api.v1.admin import content as admin_content
from app.api.v1.admin import customers, dashboard, inbox, media, orders, partner, products, users
from app.api.v1.admin import payments as admin_payments
from app.api.v1.admin import stores as admin_stores

api_router = APIRouter()
for r in (auth.router, me.router, catalog.router, checkout.router, payments.router, 
          stores.router, contact.router, content.router, analytics.router
          ):
    api_router.include_router(r)

for r in (dashboard.router, products.router, orders.router, admin_payments.router, 
          customers.router, users.router, admin_stores.router,
          inbox.router, admin_content.router, media.router, partner.router
    ):
    api_router.include_router(r)
