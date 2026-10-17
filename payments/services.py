"""Transactional payment-intent, attempt, and webhook persistence services."""

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.models import Member

from .models import (
    PAYMENT_PROVIDER_CHOICES,
    PaymentAllocation,
    PaymentAttempt,
    PaymentIntent,
    PaymentWebhookEvent,
)


PAYMENT_INTENT_LIFETIME = timedelta(minutes=15)
MONEY_QUANTUM = Decimal("0.01")
SUPPORTED_PROVIDERS = {key for key, _label in PAYMENT_PROVIDER_CHOICES}


class PaymentServiceError(Exception):
    """Client-safe payment validation or idempotency failure."""

    def __init__(self, code, message, *, fields=None):
        """Capture a stable error code and optional field-level details."""

        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}


@dataclass(frozen=True)
class PaymentAllocationInput:
    """Validated service input for one week or one non-weekly allocation."""

    amount: Decimal
    contribution_week: ContributionWeek | None = None


def normalize_tanzania_phone(phone_number):
    """Normalize a local or international Tanzania number to twelve digits."""

    digits = "".join(character for character in phone_number if character.isdigit())
    if digits.startswith("0"):
        digits = f"255{digits[1:]}"
    if not digits.startswith("255") or len(digits) != 12:
        raise PaymentServiceError(
            "PHONE_INVALID",
            "Enter a valid Tanzania mobile-money number.",
            fields={"payer_phone_number": ["Enter a valid Tanzania phone number."]},
        )
    return digits


def normalize_amount(value, field_name="amount"):
    """Return a positive two-decimal amount without silently rounding money."""

    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PaymentServiceError(
            "PAYMENT_AMOUNT_INVALID",
            "Payment amounts must be valid decimal values.",
            fields={field_name: ["Enter a valid amount."]},
        ) from error
    if (
        not amount.is_finite()
        or amount <= 0
        or amount != amount.quantize(MONEY_QUANTUM)
    ):
        raise PaymentServiceError(
            "PAYMENT_AMOUNT_INVALID",
            "Payment amounts must be positive and use at most two decimal places.",
            fields={field_name: ["Use a positive amount with at most two decimals."]},
        )
    return amount


def payment_request_fingerprint(
    *,
    category,
    financial_year,
    provider,
    payer_phone_number,
    allocations,
    currency,
):
    """Hash the canonical logical request used for idempotency comparisons."""

    canonical_allocations = sorted(
        (
            {
                "contribution_week_id": (
                    str(allocation.contribution_week.public_id)
                    if allocation.contribution_week
                    else None
                ),
                "amount": format(normalize_amount(allocation.amount), "f"),
            }
            for allocation in allocations
        ),
        key=lambda item: (item["contribution_week_id"] or "", item["amount"]),
    )
    body = {
        "category_id": str(category.public_id),
        "financial_year_id": str(financial_year.public_id),
        "provider": provider,
        "payment_method": "mobile_money",
        "payer_phone_number": normalize_tanzania_phone(payer_phone_number),
        "currency": currency.upper(),
        "allocations": canonical_allocations,
    }
    serialized = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_payment_scope(
    *,
    member,
    category,
    financial_year,
    provider,
    allocations,
    currency,
):
    """Enforce member, category, period, provider, and amount eligibility."""

    if (
        not member.user.is_active
        or not member.church.is_active
        or not member.is_active
        or member.approval_status != "APPROVED"
    ):
        raise PaymentServiceError(
            "MEMBER_NOT_APPROVED",
            "Only active, approved members can make payments.",
        )
    if member.church_id != category.church_id:
        raise PaymentServiceError(
            "CATEGORY_NOT_FOUND",
            "Contribution category not found.",
        )
    if member.church_id != financial_year.church_id:
        raise PaymentServiceError(
            "FINANCIAL_YEAR_NOT_FOUND",
            "Financial year not found.",
        )
    if not financial_year.is_active:
        raise PaymentServiceError(
            "FINANCIAL_YEAR_INACTIVE",
            "Payments can only be made in the active financial year.",
        )
    if not category.is_active or not category.is_mobile_visible:
        raise PaymentServiceError(
            "CATEGORY_NOT_FOUND",
            "Contribution category not found.",
        )
    if not category.allows_member_payment:
        raise PaymentServiceError(
            "CATEGORY_PAYMENT_DISABLED",
            "This contribution category does not accept mobile payments.",
        )
    if provider not in SUPPORTED_PROVIDERS:
        raise PaymentServiceError(
            "PAYMENT_PROVIDER_UNKNOWN",
            "Payment provider is not supported.",
        )
    if currency.upper() != "TZS":
        raise PaymentServiceError(
            "PAYMENT_CURRENCY_UNSUPPORTED",
            "Mobile payments currently support TZS only.",
        )
    if not allocations:
        raise PaymentServiceError(
            "PAYMENT_ALLOCATIONS_REQUIRED",
            "Select at least one contribution period.",
        )

    seen_week_ids = set()
    is_weekly = category.frequency == "WEEKLY"
    for index, allocation in enumerate(allocations):
        normalize_amount(allocation.amount, f"allocations.{index}.amount")
        week = allocation.contribution_week
        if is_weekly and week is None:
            raise PaymentServiceError(
                "PAYMENT_WEEK_REQUIRED",
                "Weekly contribution categories require a contribution week.",
            )
        if not is_weekly and week is not None:
            raise PaymentServiceError(
                "PAYMENT_WEEK_NOT_ALLOWED",
                "This contribution category does not use weekly allocations.",
            )
        if week:
            if week.pk in seen_week_ids:
                raise PaymentServiceError(
                    "PAYMENT_WEEK_DUPLICATE",
                    "A contribution week can only appear once in a payment.",
                )
            seen_week_ids.add(week.pk)
            if week.church_id != member.church_id:
                raise PaymentServiceError(
                    "CONTRIBUTION_WEEK_NOT_FOUND",
                    "Contribution week not found.",
                )
            if week.financial_year_id != financial_year.id:
                raise PaymentServiceError(
                    "PAYMENT_WEEK_OUTSIDE_YEAR",
                    "Every contribution week must belong to the selected financial year.",
                )
            if week.sunday_date > timezone.localdate():
                raise PaymentServiceError(
                    "PAYMENT_WEEK_NOT_OPEN",
                    "Future contribution weeks cannot be paid yet.",
                )
            if not week.is_active and not category.allows_catch_up:
                raise PaymentServiceError(
                    "CATEGORY_CATCH_UP_DISABLED",
                    "This contribution category does not allow payments for earlier weeks.",
                )

    if not is_weekly and len(allocations) != 1:
        raise PaymentServiceError(
            "PAYMENT_ALLOCATION_INVALID",
            "Non-weekly categories require one allocation.",
        )

    total = sum(
        (normalize_amount(item.amount) for item in allocations),
        Decimal("0.00"),
    )
    if category.minimum_amount is not None and total < category.minimum_amount:
        raise PaymentServiceError(
            "PAYMENT_AMOUNT_BELOW_MINIMUM",
            f"The minimum payment amount is {category.minimum_amount} TZS.",
        )
    if category.maximum_amount is not None and total > category.maximum_amount:
        raise PaymentServiceError(
            "PAYMENT_AMOUNT_ABOVE_MAXIMUM",
            f"The maximum payment amount is {category.maximum_amount} TZS.",
        )
    return total


def _existing_idempotent_intent(member, idempotency_key, fingerprint):
    """Return an existing matching intent or reject key reuse with new data."""

    existing = PaymentIntent.objects.filter(
        member=member,
        idempotency_key=idempotency_key,
    ).first()
    if not existing:
        return None
    if existing.request_fingerprint != fingerprint:
        raise PaymentServiceError(
            "IDEMPOTENCY_CONFLICT",
            "This idempotency key was already used for another payment request.",
        )
    return existing


def create_payment_intent(
    *,
    member: Member,
    category: ContributionCategory,
    financial_year: FinancialYear,
    provider: str,
    payer_phone_number: str,
    idempotency_key,
    allocations: list[PaymentAllocationInput],
    currency="TZS",
):
    """Persist one validated intent and its allocations exactly once."""

    allocations = list(allocations)
    fingerprint = payment_request_fingerprint(
        category=category,
        financial_year=financial_year,
        provider=provider,
        payer_phone_number=payer_phone_number,
        allocations=allocations,
        currency=currency,
    )
    existing = _existing_idempotent_intent(member, idempotency_key, fingerprint)
    if existing:
        return existing, False

    total = validate_payment_scope(
        member=member,
        category=category,
        financial_year=financial_year,
        provider=provider,
        allocations=allocations,
        currency=currency,
    )
    phone_number = normalize_tanzania_phone(payer_phone_number)

    try:
        with transaction.atomic():
            intent = PaymentIntent(
                church=member.church,
                member=member,
                category=category,
                financial_year=financial_year,
                provider=provider,
                payer_phone_number=phone_number,
                amount=total,
                currency=currency.upper(),
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                expires_at=timezone.now() + PAYMENT_INTENT_LIFETIME,
            )
            intent.reference = f"BHS-{intent.public_id.hex.upper()}"
            intent.full_clean()
            intent.save()
            for allocation_input in allocations:
                allocation = PaymentAllocation(
                    payment_intent=intent,
                    contribution_week=allocation_input.contribution_week,
                    amount=normalize_amount(allocation_input.amount),
                )
                allocation.full_clean()
                allocation.save()
            return intent, True
    except IntegrityError:
        # A concurrent request may win the member/key uniqueness race. Resolve it
        # as a normal idempotent replay while allowing unrelated integrity errors
        # to retain their original traceback.
        existing = _existing_idempotent_intent(member, idempotency_key, fingerprint)
        if existing:
            return existing, False
        raise


@transaction.atomic
def create_payment_attempt(payment_intent):
    """Create the next sequential provider attempt under an intent row lock."""

    locked_intent = PaymentIntent.objects.select_for_update().get(pk=payment_intent.pk)
    latest_number = locked_intent.attempts.aggregate(number=Max("attempt_number"))[
        "number"
    ] or 0
    attempt = PaymentAttempt(
        payment_intent=locked_intent,
        attempt_number=latest_number + 1,
        provider=locked_intent.provider,
    )
    attempt.full_clean()
    attempt.save()
    return attempt


def webhook_payload_hash(raw_body):
    """Hash exact callback bytes for replay detection without log exposure."""

    return hashlib.sha256(raw_body).hexdigest()


def record_webhook_event(
    *,
    provider,
    raw_body,
    payload,
    signature_valid,
    external_event_id="",
    payment_intent=None,
    request_id="",
    source_ip=None,
):
    """Persist one callback once and return whether it was newly recorded."""

    if provider not in SUPPORTED_PROVIDERS:
        raise PaymentServiceError(
            "PAYMENT_PROVIDER_UNKNOWN",
            "Payment provider is not supported.",
        )
    payload_hash = webhook_payload_hash(raw_body)
    try:
        with transaction.atomic():
            event = PaymentWebhookEvent.objects.create(
                provider=provider,
                payment_intent=payment_intent,
                external_event_id=external_event_id,
                payload_hash=payload_hash,
                payload=payload,
                signature_valid=signature_valid,
                request_id=request_id,
                source_ip=source_ip,
            )
            return event, True
    except IntegrityError:
        event = PaymentWebhookEvent.objects.filter(
            provider=provider,
            payload_hash=payload_hash,
        ).first()
        if not event and external_event_id:
            event = PaymentWebhookEvent.objects.filter(
                provider=provider,
                external_event_id=external_event_id,
            ).first()
        if event:
            return event, False
        raise
