from ninja import Schema

from api.common.schemas import PageSchema


class PaymentMethodListSchema(Schema):
    """Wrap payment methods currently enabled for a member."""

    items: list[dict]


class PaymentIntentListSchema(Schema):
    """Wrap cursor-paginated payment intents once persistence is enabled."""

    items: list[dict]
    page: PageSchema
