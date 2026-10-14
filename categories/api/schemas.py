from uuid import UUID

from ninja import Schema

from api.common.schemas import MoneySchema, PageSchema


class LabelsSchema(Schema):
    """Provide default and Swahili category labels."""

    default: str
    sw: str


class AmountGuidanceSchema(Schema):
    """Describe optional suggested and allowed contribution amounts."""

    suggested: MoneySchema | None
    minimum: MoneySchema | None
    maximum: MoneySchema | None


class CategoryCardSchema(Schema):
    """Describe one configurable contribution card and member summary."""

    id: UUID
    key: str
    labels: LabelsSchema
    description: str
    icon: str
    color: str
    frequency: str
    display_order: int
    payments_enabled: bool
    allows_catch_up: bool
    amount_guidance: AmountGuidanceSchema
    missing_weeks_count: int
    total_contributed: MoneySchema


class CategoryListSchema(Schema):
    """Wrap mobile contribution cards returned for a financial year."""

    items: list[CategoryCardSchema]


class WeekSchema(Schema):
    """Describe one contribution week's state and payment eligibility."""

    id: UUID
    week_number: int
    sunday_date: str
    state: str
    payment_eligible: bool
    contributed: MoneySchema
    expected: MoneySchema | None
    remaining: MoneySchema | None


class WeekListSchema(Schema):
    """Wrap a cursor-paginated category week schedule."""

    items: list[WeekSchema]
    page: PageSchema
