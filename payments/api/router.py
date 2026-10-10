from uuid import UUID

from ninja import Body, Router

from api.common.errors import ApiError
from api.common.schemas import ErrorSchema
from payments.api.schemas import PaymentIntentListSchema, PaymentMethodListSchema
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["payments"])


def payments_unavailable():
    raise ApiError(
        "PAYMENTS_UNAVAILABLE",
        "Mobile payments are not configured yet.",
        status=503,
    )


@router.get("/payment-methods", response=PaymentMethodListSchema)
def payment_methods(request):
    return {"items": []}


@router.post("/payment-intents", response={503: ErrorSchema})
def create_payment_intent(request, payload: Body[dict]):
    payments_unavailable()


@router.get("/payment-intents", response=PaymentIntentListSchema)
def payment_intents(request):
    return {
        "items": [],
        "page": {"next_cursor": None, "has_more": False},
    }


@router.get(
    "/payment-intents/{payment_intent_id}",
    response={503: ErrorSchema},
)
def payment_intent_detail(request, payment_intent_id: UUID):
    payments_unavailable()


@router.post(
    "/payment-intents/{payment_intent_id}/cancel",
    response={503: ErrorSchema},
)
def cancel_payment_intent(request, payment_intent_id: UUID):
    payments_unavailable()
