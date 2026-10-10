from ninja import Schema

from api.common.schemas import PageSchema


class PaymentMethodListSchema(Schema):
    items: list[dict]


class PaymentIntentListSchema(Schema):
    items: list[dict]
    page: PageSchema
