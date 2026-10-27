import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover
        return self.value


class Permission(StrEnum):
    DASHBOARD_VIEW = "dashboard:view"
    ANALYTICS_VIEW = "analytics:view"
    PRODUCTS_VIEW = "products:view"
    PRODUCTS_MANAGE = "products:manage"
    PROMOTIONS_MANAGE = "promotions:manage"
    ORDERS_VIEW = "orders:view"
    ORDERS_MANAGE = "orders:manage"
    PAYMENTS_VIEW = "payments:view"
    PAYMENTS_CONFIRM = "payments:confirm"
    CUSTOMERS_VIEW = "customers:view"
    CUSTOMERS_MANAGE = "customers:manage"
    USERS_MANAGE = "users:manage"
    ROLES_MANAGE = "roles:manage"
    STORES_VIEW = "stores:view"
    STORES_MANAGE = "stores:manage"
    EMAILS_MANAGE = "emails:manage"
    CONTACTS_MANAGE = "contacts:manage"
    CONTENT_MANAGE = "content:manage"
    SETTINGS_MANAGE = "settings:manage"
    PARTNER_PORTAL = "partner:portal"


class UserType(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    PARTNER = "partner"


class OrderStatus(StrEnum):
    PENDING = "pending"                    # created, awaiting payment / confirmation
    CONFIRMED = "confirmed"                # payment received or admin confirmed
    PROCESSING = "processing"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    PAYSTACK = "paystack"
    BANK_TRANSFER = "bank_transfer"
    WHATSAPP = "whatsapp"
    CASH = "cash"
    INVOICE = "invoice"


class PaymentProvider(StrEnum):
    PAYSTACK = "paystack"
    MANUAL = "manual"


class PaymentPurpose(StrEnum):
    ORDER = "order"
    DIRECT = "direct"


class OrderChannel(StrEnum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    EMAIL = "email"
    ADMIN = "admin"
    STORE = "store"


class StoreType(StrEnum):
    STORE = "store"
    DISTRIBUTOR = "distributor"
    DEALER = "dealer"


class StoreStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class AssignmentStatus(StrEnum):
    NONE = "none"
    SUGGESTED = "suggested"   # system suggestion awaiting admin approval
    ASSIGNED = "assigned"
    REJECTED = "rejected"


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


class ContactSubject(StrEnum):
    GENERAL = "general"
    WHOLESALE = "wholesale"
    DISTRIBUTION = "distribution"
    EVENT = "event"
    COMPLAINT = "complaint"


class ContactStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SPAM = "spam"


class EmailDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ApplicationStatus(StrEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class RecipeCategory(StrEnum):
    COCKTAIL = "cocktail"
    WARM = "warm_drink"
    SHOT = "shot"
    MOCKTAIL = "mocktail"
