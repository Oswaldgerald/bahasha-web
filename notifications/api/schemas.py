from datetime import datetime
from uuid import UUID

from ninja import Schema

from api.common.schemas import PageSchema


class NotificationSchema(Schema):
    """Describe a visible notification and its member-specific read state."""

    id: UUID
    title: str
    message: str
    notification_type: str
    sent_at: datetime | None
    is_read: bool
    read_at: datetime | None


class NotificationListSchema(Schema):
    """Wrap cursor-paginated member notifications."""

    items: list[NotificationSchema]
    page: PageSchema


class DeviceRequestSchema(Schema):
    """Validate mobile installation and push-token registration data."""

    installation_id: UUID
    platform: str
    push_token: str
    app_version: str = ""


class DeviceSchema(Schema):
    """Describe registered device metadata safe to return to clients."""

    id: UUID
    installation_id: UUID
    platform: str
    app_version: str
    is_active: bool
