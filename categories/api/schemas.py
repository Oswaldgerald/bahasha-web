from uuid import UUID

from ninja import Schema

from api.common.schemas import MoneySchema, PageSchema


class LabelsSchema(Schema):
    default: str
    sw: str


class AmountGuidanceSchema(Schema):
    suggested: MoneySchema | None
    minimum: MoneySchema | None
    maximum: MoneySchema | None


class CategoryCardSchema(Schema):
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
    items: list[CategoryCardSchema]


class WeekSchema(Schema):
    id: UUID
    week_number: int
    sunday_date: str
    state: str
    payment_eligible: bool
    contributed: MoneySchema
    expected: MoneySchema | None
    remaining: MoneySchema | None


class WeekListSchema(Schema):
    items: list[WeekSchema]
    page: PageSchema
