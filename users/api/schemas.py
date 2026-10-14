from uuid import UUID

from ninja import Schema


class DeviceSchema(Schema):
    """Describe the mobile installation requesting an API session."""

    installation_id: UUID
    platform: str
    app_version: str = ""
    device_name: str = ""


class TokenRequestSchema(Schema):
    """Validate member credentials and device metadata for sign-in."""

    identifier: str
    password: str
    device: DeviceSchema


class RefreshRequestSchema(Schema):
    """Validate a refresh-token rotation request."""

    refresh_token: str


class PasswordForgotSchema(Schema):
    """Validate the email used for a non-enumerating recovery request."""

    email: str


class TokenMemberSchema(Schema):
    """Provide compact member identity in authentication responses."""

    id: UUID
    full_name: str
    approval_status: str


class TokenResponseSchema(Schema):
    """Describe issued opaque credentials and their access lifetime."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    member: TokenMemberSchema
