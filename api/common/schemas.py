from typing import Any

from ninja import Schema


class MoneySchema(Schema):
    amount: str
    currency: str = "TZS"


class PageSchema(Schema):
    next_cursor: str | None = None
    has_more: bool


class ErrorDetailSchema(Schema):
    code: str
    message: str
    fields: dict[str, list[str]] | dict[str, Any]
    request_id: str


class ErrorSchema(Schema):
    error: ErrorDetailSchema


class MessageSchema(Schema):
    message: str
