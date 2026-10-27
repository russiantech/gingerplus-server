"""Permission catalogue + default roles. Roles are stored in DB and can be edited by admins."""
from app.enums import Permission as P

DEFAULT_ROLES: dict[str, dict] = {
    "super_admin": {"name": "Super Admin", "description": "Full access", "permissions": [p.value for p in P]},
    "admin": {
        "name": "Admin",
        "description": "Manage everything except roles/system",
        "permissions": [p.value for p in P if p not in (P.ROLES_MANAGE, P.SETTINGS_MANAGE)],
    },
    "sales_manager": {
        "name": "Sales Manager",
        "description": "Orders, payments, customers, stores",
        "permissions": [
            P.DASHBOARD_VIEW, P.ORDERS_VIEW, P.ORDERS_MANAGE, P.PAYMENTS_VIEW, P.PAYMENTS_CONFIRM,
            P.CUSTOMERS_VIEW, P.STORES_VIEW, P.STORES_MANAGE, P.PRODUCTS_VIEW, P.PROMOTIONS_MANAGE, P.ANALYTICS_VIEW,
        ],
    },
    "support_agent": {
        "name": "Support Agent",
        "description": "Inbox, contact messages and order lookup",
        "permissions": [P.DASHBOARD_VIEW, P.EMAILS_MANAGE, P.CONTACTS_MANAGE, P.ORDERS_VIEW, P.CUSTOMERS_VIEW],
    },
    "content_editor": {
        "name": "Content Editor",
        "description": "Pages, blog, recipes, testimonials",
        "permissions": [P.DASHBOARD_VIEW, P.CONTENT_MANAGE, P.PRODUCTS_VIEW, P.PRODUCTS_MANAGE],
    },
    "store_partner": {"name": "Store / Distributor", "description": "Partner portal", "permissions": [P.PARTNER_PORTAL]},
    "customer": {"name": "Customer", "description": "Storefront customer", "permissions": []},
}
