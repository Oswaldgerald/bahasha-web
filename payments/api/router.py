"""Member payment HTTP contract.

Routes remain unavailable until payment-intent persistence, idempotency, and
verified settlement are implemented. The provider adapter alone is not sufficient
to safely create posted contributions.
"""

from uuid import UUID

from ninja import Body, Router

from api.common.errors import ApiError
from api.common.schemas import ErrorSchema
from payments.api.schemas import PaymentIntentListSchema, PaymentMethodListSchema
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["payments"])


def payments_unavailable():
    """Return a stable error while the payment safety boundary is incomplete."""

    raise ApiError(
        "PAYMENTS_UNAVAILABLE",
        "Mobile payments are not configured yet.",
        status=503,
    )


@router.get("/payment-methods", response=PaymentMethodListSchema)
def payment_methods(request):
    """Return no methods until the complete payment safety gate is enabled."""

    return {"items": []}


@router.post("/payment-intents", response={503: ErrorSchema})
def create_payment_intent(request, payload: Body[dict]):
    """Reject intent creation until durable, idempotent persistence exists."""

    payments_unavailable()


@router.get("/payment-intents", response=PaymentIntentListSchema)
def payment_intents(request):
    """Return the empty intent history while mobile payments remain disabled."""

    return {
        "items": [],
        "page": {"next_cursor": None, "has_more": False},
    }


@router.get(
    "/payment-intents/{payment_intent_id}",
    response={503: ErrorSchema},
)
def payment_intent_detail(request, payment_intent_id: UUID):
    """Reject intent polling until persisted payment intents are available."""

    payments_unavailable()


@router.post(
    "/payment-intents/{payment_intent_id}/cancel",
    response={503: ErrorSchema},
)
def cancel_payment_intent(request, payment_intent_id: UUID):
    """Reject cancellation until provider-aware intent state handling exists."""

    payments_unavailable()
