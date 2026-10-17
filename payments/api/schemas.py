from decimal import Decimal
from uuid import UUID

from ninja import Schema

from api.common.schemas import MoneySchema, PageSchema


class PaymentMethodSchema(Schema):
    """Describe one enabled payment method and its available providers."""

    key: str
    name: str
    providers: list[str]
    currency: str
    enabled: bool


class PaymentMethodListSchema(Schema):
    """Wrap payment methods currently enabled for a member."""

    items: list[PaymentMethodSchema]


class PaymentAllocationCreateSchema(Schema):
    """Allocate part of a payment to one weekly contribution period."""

    contribution_week_id: UUID | None = None
    amount: Decimal


class PaymentIntentCreateSchema(Schema):
    """Validate the member-controlled portion of a payment request."""

    category_id: UUID
    financial_year_id: UUID
    payment_method: str = "mobile_money"
    provider: str
    payer_phone_number: str
    allocations: list[PaymentAllocationCreateSchema]


class PaymentCategoryReferenceSchema(Schema):
    """Identify the contribution category selected for payment."""

    id: UUID
    key: str
    name: str


class PaymentWeekReferenceSchema(Schema):
    """Identify a weekly contribution period inside an allocation."""

    id: UUID
    number: int
    sunday_date: str


class PaymentAllocationSchema(Schema):
    """Describe one persisted payment allocation and posted contribution."""

    id: UUID
    week: PaymentWeekReferenceSchema | None
    amount: MoneySchema
    contribution_id: UUID | None


class PaymentNextActionSchema(Schema):
    """Tell the mobile client what the member should do next."""

    type: str
    message: str


class PaymentIntentSchema(Schema):
    """Expose member-safe payment state without internal database identifiers."""

    id: UUID
    reference: str
    status: str
    provider: str
    amount: MoneySchema
    category: PaymentCategoryReferenceSchema
    allocations: list[PaymentAllocationSchema]
    provider_reference: str | None
    contribution_ids: list[UUID]
    expires_at: str
    created_at: str
    next_action: PaymentNextActionSchema | None


class PaymentIntentListSchema(Schema):
    """Wrap cursor-paginated payment intents owned by one member."""

    items: list[PaymentIntentSchema]
    page: PageSchema
