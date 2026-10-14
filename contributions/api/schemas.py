from uuid import UUID

from ninja import Schema

from api.common.schemas import MoneySchema, PageSchema


class YearSchema(Schema):
    """Describe a church financial year using a public identifier."""

    id: UUID
    year: int
    start_date: str
    end_date: str
    is_active: bool


class YearListSchema(Schema):
    """Wrap financial years visible to the authenticated member."""

    items: list[YearSchema]


class CategoryReferenceSchema(Schema):
    """Embed compact category identity in contribution responses."""

    id: UUID
    key: str
    name: str


class WeekReferenceSchema(Schema):
    """Embed compact week identity in contribution responses."""

    id: UUID
    number: int
    sunday_date: str


class ContributionSchema(Schema):
    """Describe one member contribution in a list response."""

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
    """Extend a contribution with financial, church, and remark details."""

    financial_year: YearSchema
    remarks: str
    church: dict


class ContributionListSchema(Schema):
    """Wrap cursor-paginated member contribution history."""

    items: list[ContributionSchema]
    page: PageSchema


class TargetSchema(Schema):
    """Describe annual target progress for one contribution category."""

    id: UUID
    financial_year: dict
    category: CategoryReferenceSchema
    target: MoneySchema
    contributed: MoneySchema
    remaining: MoneySchema
    completion_percentage: str


class TargetListSchema(Schema):
    """Wrap cursor-paginated annual targets."""

    items: list[TargetSchema]
    page: PageSchema
