from uuid import UUID

from ninja import Schema

from categories.api.schemas import CategoryCardSchema


class NamedReferenceSchema(Schema):
    """Represent a related object by public ID and display name."""

    id: UUID
    name: str


class ChurchReferenceSchema(NamedReferenceSchema):
    """Extend a named reference with the church's stable code."""

    code: str


class MemberSchema(Schema):
    """Describe the authenticated member profile returned to mobile."""

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
    """Limit member self-service updates to approved profile fields."""

    full_name: str | None = None
    email: str | None = None


class ActiveYearSchema(Schema):
    """Identify the active financial year in bootstrap data."""

    id: UUID
    year: int


class ActiveWeekSchema(Schema):
    """Describe the active contribution week in bootstrap data."""

    id: UUID
    number: int
    sunday_date: str
    is_closed: bool


class ActivePeriodSchema(Schema):
    """Group optional active year and week records."""

    financial_year: ActiveYearSchema | None
    week: ActiveWeekSchema | None


class CapabilitySchema(Schema):
    """Advertise server features currently safe for the mobile client."""

    payments_enabled: bool
    profile_photo_upload: bool
    push_notifications: bool


class BootstrapSchema(Schema):
    """Describe the complete initial payload required by the mobile home screen."""

    member: MemberSchema
    active_period: ActivePeriodSchema
    categories: list[CategoryCardSchema]
    unread_notifications_count: int
    capabilities: CapabilitySchema
