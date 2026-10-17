"""Authenticated member payment endpoints with a development-only mock mode."""

from uuid import UUID

from django.conf import settings
from ninja import Header, Router

from api.common.errors import ApiError
from api.common.pagination import paginate
from api.common.schemas import ErrorSchema
from categories.api.services import money
from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from payments.api.schemas import (
    PaymentIntentCreateSchema,
    PaymentIntentListSchema,
    PaymentIntentSchema,
    PaymentMethodListSchema,
)
from payments.models import PAYMENT_PROVIDER_CHOICES, PaymentIntent
from payments.providers import PaymentProviderError
from payments.services import (
    PaymentAllocationInput,
    PaymentServiceError,
    create_payment_intent as persist_payment_intent,
    initiate_payment_intent,
    reconcile_payment_intent,
    transition_payment_intent,
)
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["payments"])
PROVIDER_LABELS = dict(PAYMENT_PROVIDER_CHOICES)


def ensure_payments_enabled():
    """Keep every member payment route behind the server-side feature flag."""

    if not settings.PAYMENTS_ENABLED:
        raise ApiError(
            "PAYMENTS_UNAVAILABLE",
            "Mobile payments are not configured yet.",
            status=503,
        )


def payment_api_error(error):
    """Translate service failures into stable HTTP error semantics."""

    status = {
        "IDEMPOTENCY_CONFLICT": 409,
        "PAYMENT_ALREADY_STARTED": 409,
        "PAYMENT_STATUS_CONFLICT": 409,
        "PAYMENT_EXPIRED": 409,
    }.get(error.code, 422)
    return ApiError(error.code, error.message, status=status, fields=error.fields)


def provider_api_error(error):
    """Expose only the sanitized provider code and message."""

    return ApiError(error.code, error.message, status=502)


def owned_intent(request, payment_intent_id):
    """Resolve a payment only when it belongs to the authenticated member."""

    try:
        return (
            PaymentIntent.objects.select_related("category", "financial_year")
            .prefetch_related(
                "allocations__contribution_week",
                "allocations__contribution",
            )
            .get(
                public_id=payment_intent_id,
                member=request.auth.member,
                church=request.auth.member.church,
            )
        )
    except PaymentIntent.DoesNotExist as error:
        raise ApiError(
            "NOT_FOUND",
            "The payment intent was not found.",
            status=404,
        ) from error


def payment_intent_payload(payment_intent):
    """Serialize a payment intent and its allocations for the mobile client."""

    allocations = list(
        payment_intent.allocations.select_related(
            "contribution_week",
            "contribution",
        ).order_by("created_at")
    )
    allocation_items = []
    contribution_ids = []
    for allocation in allocations:
        week = allocation.contribution_week
        contribution = allocation.contribution
        if contribution:
            contribution_ids.append(contribution.public_id)
        allocation_items.append(
            {
                "id": allocation.public_id,
                "week": (
                    {
                        "id": week.public_id,
                        "number": week.week_number,
                        "sunday_date": week.sunday_date.isoformat(),
                    }
                    if week
                    else None
                ),
                "amount": money(allocation.amount),
                "contribution_id": contribution.public_id if contribution else None,
            }
        )
    next_action = None
    if payment_intent.status == "pending_customer_action":
        next_action = {
            "type": "approve_mobile_money_prompt",
            "message": "Approve the payment request on your phone.",
        }
    elif payment_intent.status == "processing":
        next_action = {
            "type": "wait_for_confirmation",
            "message": "The payment is being confirmed.",
        }
    return {
        "id": payment_intent.public_id,
        "reference": payment_intent.reference,
        "status": payment_intent.status,
        "provider": payment_intent.provider,
        "amount": money(payment_intent.amount),
        "category": {
            "id": payment_intent.category.public_id,
            "key": payment_intent.category.key,
            "name": payment_intent.category.name,
        },
        "allocations": allocation_items,
        "provider_reference": payment_intent.provider_reference or None,
        "contribution_ids": contribution_ids,
        "expires_at": payment_intent.expires_at.isoformat().replace("+00:00", "Z"),
        "created_at": payment_intent.created_at.isoformat().replace("+00:00", "Z"),
        "next_action": next_action,
    }


@router.get(
    "/payment-methods",
    response=PaymentMethodListSchema,
)
def payment_methods(request):
    """List providers available under the enabled payment mode."""

    if not settings.PAYMENTS_ENABLED:
        return {"items": []}
    providers = (
        list(PROVIDER_LABELS)
        if settings.PAYMENT_PROVIDER_MODE == "mock"
        else [settings.PAYMENT_PROVIDER]
    )
    return {
        "items": [
            {
                "key": "mobile_money",
                "name": "Mobile money",
                "providers": providers,
                "currency": "TZS",
                "enabled": True,
            }
        ]
    }


@router.post(
    "/payment-intents",
    response={
        202: PaymentIntentSchema,
        409: ErrorSchema,
        422: ErrorSchema,
        502: ErrorSchema,
        503: ErrorSchema,
    },
)
def create_payment_intent(
    request,
    payload: PaymentIntentCreateSchema,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """Create an idempotent intent and request a mobile-money prompt."""

    ensure_payments_enabled()
    if payload.payment_method != "mobile_money":
        raise ApiError(
            "PAYMENT_METHOD_UNSUPPORTED",
            "Only mobile money is currently supported.",
            status=422,
            fields={"payment_method": ["Use mobile_money."]},
        )
    try:
        key = UUID(idempotency_key or "")
    except ValueError as error:
        raise ApiError(
            "IDEMPOTENCY_KEY_INVALID",
            "A valid Idempotency-Key header is required.",
            status=422,
            fields={"Idempotency-Key": ["Enter a valid UUID."]},
        ) from error

    member = request.auth.member
    try:
        category = ContributionCategory.objects.get(
            public_id=payload.category_id,
            church=member.church,
        )
        financial_year = FinancialYear.objects.get(
            public_id=payload.financial_year_id,
            church=member.church,
        )
    except (ContributionCategory.DoesNotExist, FinancialYear.DoesNotExist) as error:
        raise ApiError(
            "NOT_FOUND",
            "The selected category or financial year was not found.",
            status=404,
        ) from error
    if category.frequency != "WEEKLY":
        raise ApiError(
            "PAYMENT_PERIOD_UNSUPPORTED",
            "Simulated payments currently support weekly categories only.",
            status=422,
        )

    week_ids = {
        item.contribution_week_id
        for item in payload.allocations
        if item.contribution_week_id
    }
    weeks = {
        week.public_id: week
        for week in ContributionWeek.objects.filter(
            public_id__in=week_ids,
            church=member.church,
        )
    }
    if len(weeks) != len(week_ids):
        raise ApiError(
            "CONTRIBUTION_WEEK_NOT_FOUND",
            "One or more contribution weeks were not found.",
            status=404,
        )
    allocations = [
        PaymentAllocationInput(
            amount=item.amount,
            contribution_week=weeks.get(item.contribution_week_id),
        )
        for item in payload.allocations
    ]
    try:
        intent, _created = persist_payment_intent(
            member=member,
            category=category,
            financial_year=financial_year,
            provider=payload.provider,
            payer_phone_number=payload.payer_phone_number,
            idempotency_key=key,
            allocations=allocations,
        )
        if intent.status == "created":
            intent, _attempt = initiate_payment_intent(intent)
    except PaymentServiceError as error:
        raise payment_api_error(error) from error
    except PaymentProviderError as error:
        if error.retryable:
            intent.refresh_from_db()
        else:
            raise provider_api_error(error) from error
    intent = owned_intent(request, intent.public_id)
    return 202, payment_intent_payload(intent)


@router.get(
    "/payment-intents",
    response={200: PaymentIntentListSchema, 503: ErrorSchema},
)
def payment_intents(request, cursor: str | None = None, page_size: int = 20):
    """Return recent member-owned payment requests and their current states."""

    ensure_payments_enabled()
    queryset = (
        PaymentIntent.objects.filter(
            member=request.auth.member,
            church=request.auth.member.church,
        )
        .select_related("category")
        .prefetch_related(
            "allocations__contribution_week",
            "allocations__contribution",
        )
        .order_by("-created_at")
    )
    items, page = paginate(queryset, cursor=cursor, page_size=page_size)
    return {
        "items": [payment_intent_payload(item) for item in items],
        "page": page,
    }


@router.get(
    "/payment-intents/{payment_intent_id}",
    response={
        200: PaymentIntentSchema,
        404: ErrorSchema,
        422: ErrorSchema,
        502: ErrorSchema,
        503: ErrorSchema,
    },
)
def payment_intent_detail(request, payment_intent_id: UUID):
    """Poll payment state and reconcile the deterministic mock provider."""

    ensure_payments_enabled()
    intent = owned_intent(request, payment_intent_id)
    if (
        settings.PAYMENT_PROVIDER_MODE == "mock"
        and intent.status in {"pending_customer_action", "processing"}
    ):
        try:
            reconcile_payment_intent(intent)
        except PaymentServiceError as error:
            raise payment_api_error(error) from error
        except PaymentProviderError as error:
            raise provider_api_error(error) from error
        intent = owned_intent(request, payment_intent_id)
    return payment_intent_payload(intent)


@router.post(
    "/payment-intents/{payment_intent_id}/cancel",
    response={
        200: PaymentIntentSchema,
        404: ErrorSchema,
        409: ErrorSchema,
        503: ErrorSchema,
    },
)
def cancel_payment_intent(request, payment_intent_id: UUID):
    """Cancel a member-owned intent while it is still awaiting authorization."""

    ensure_payments_enabled()
    intent = owned_intent(request, payment_intent_id)
    try:
        intent = transition_payment_intent(intent, "cancelled")
    except PaymentServiceError as error:
        raise payment_api_error(error) from error
    intent = owned_intent(request, intent.public_id)
    return payment_intent_payload(intent)
