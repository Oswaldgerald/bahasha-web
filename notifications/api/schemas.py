from datetime import datetime
from uuid import UUID

from ninja import Schema

from api.common.schemas import PageSchema


class NotificationSchema(Schema):
    id: UUID
    title: str
    message: str
    notification_type: str
    sent_at: datetime | None
    is_read: bool
    read_at: datetime | None


class NotificationListSchema(Schema):
    items: list[NotificationSchema]
    page: PageSchema


class DeviceRequestSchema(Schema):
    installation_id: UUID
    platform: str
    push_token: str
    app_version: str = ""


class DeviceSchema(Schema):
    id: UUID
    installation_id: UUID
    platform: str
    app_version: str
    is_active: bool
