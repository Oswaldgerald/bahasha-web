from uuid import UUID

from ninja import Schema

from api.common.schemas import MoneySchema, PageSchema


class YearSchema(Schema):
    id: UUID
    year: int
    start_date: str
    end_date: str
    is_active: bool


class YearListSchema(Schema):
    items: list[YearSchema]


class CategoryReferenceSchema(Schema):
    id: UUID
    key: str
    name: str


class WeekReferenceSchema(Schema):
    id: UUID
    number: int
    sunday_date: str


class ContributionSchema(Schema):
    id: UUID
    reference: str
    category: CategoryReferenceSchema
    week: WeekReferenceSchema
    amount: MoneySchema
    source: str
    status: str
    contribution_date: str
    posted_at: str


class ContributionDetailSchema(ContributionSchema):
    financial_year: YearSchema
    remarks: str
    church: dict


class ContributionListSchema(Schema):
    items: list[ContributionSchema]
    page: PageSchema


class TargetSchema(Schema):
    id: UUID
    financial_year: dict
    category: CategoryReferenceSchema
    target: MoneySchema
    contributed: MoneySchema
    remaining: MoneySchema
    completion_percentage: str


class TargetListSchema(Schema):
    items: list[TargetSchema]
    page: PageSchema
