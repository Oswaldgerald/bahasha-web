from uuid import UUID

from ninja import Schema


class DeviceSchema(Schema):
    installation_id: UUID
    platform: str
    app_version: str = ""
    device_name: str = ""


class TokenRequestSchema(Schema):
    identifier: str
    password: str
    device: DeviceSchema


class RefreshRequestSchema(Schema):
    refresh_token: str


class PasswordForgotSchema(Schema):
    email: str


class TokenMemberSchema(Schema):
    id: UUID
    full_name: str
    approval_status: str


class TokenResponseSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    member: TokenMemberSchema
