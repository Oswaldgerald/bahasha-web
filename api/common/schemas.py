from typing import Any

from ninja import Schema


class MoneySchema(Schema):
    """Represent money as an exact decimal string and ISO currency code."""

    amount: str
    currency: str = "TZS"


class PageSchema(Schema):
    """Describe cursor pagination state returned by list endpoints."""

    next_cursor: str | None = None
    has_more: bool


class ErrorDetailSchema(Schema):
    """Describe the stable details nested inside an API error response."""

    code: str
    message: str
    fields: dict[str, list[str]] | dict[str, Any]
    request_id: str


class ErrorSchema(Schema):
    """Wrap standardized error details for Django Ninja responses."""

    error: ErrorDetailSchema


class MessageSchema(Schema):
    """Represent a simple human-readable API acknowledgement."""

    message: str
