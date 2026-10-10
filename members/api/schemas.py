from uuid import UUID

from ninja import Schema

from categories.api.schemas import CategoryCardSchema


class NamedReferenceSchema(Schema):
    id: UUID
    name: str


class ChurchReferenceSchema(NamedReferenceSchema):
    code: str


class MemberSchema(Schema):
    id: UUID
    full_name: str
    username: str
    email: str
    phone_number: str
    bahasha_number: str
    gender: str | None
    marital_status: str | None
    approval_status: str
    photo_url: str | None
    church: ChurchReferenceSchema
    jumuiya: NamedReferenceSchema | None
    church_groups: list[NamedReferenceSchema]


class MemberUpdateSchema(Schema):
    full_name: str | None = None
    email: str | None = None


class ActiveYearSchema(Schema):
    id: UUID
    year: int


class ActiveWeekSchema(Schema):
    id: UUID
    number: int
    sunday_date: str
    is_closed: bool


class ActivePeriodSchema(Schema):
    financial_year: ActiveYearSchema | None
    week: ActiveWeekSchema | None


class CapabilitySchema(Schema):
    payments_enabled: bool
    profile_photo_upload: bool
    push_notifications: bool


class BootstrapSchema(Schema):
    member: MemberSchema
    active_period: ActivePeriodSchema
    categories: list[CategoryCardSchema]
    unread_notifications_count: int
    capabilities: CapabilitySchema
