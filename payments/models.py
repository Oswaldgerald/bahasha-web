"""Durable, provider-neutral payment records and settlement evidence."""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from categories.models import ContributionCategory
from churches.models import Church
from contributions.models import Contribution
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.models import Member


PAYMENT_PROVIDER_CHOICES = [
    ("vodacom_m_pesa", "Vodacom M-Pesa"),
    ("airtel_money", "Airtel Money"),
    ("mixx_by_yas", "Mixx by Yas"),
]


class PaymentIntent(models.Model):
    """One idempotent member request to collect and allocate mobile money."""

    STATUS_CHOICES = [
        ("created", "Created"),
        ("pending_customer_action", "Pending customer action"),
        ("processing", "Processing"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_METHOD_CHOICES = [("mobile_money", "Mobile money")]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    church = models.ForeignKey(
        Church,
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    provider = models.CharField(max_length=40, choices=PAYMENT_PROVIDER_CHOICES)
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="mobile_money",
    )
    payer_phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="created",
    )
    idempotency_key = models.UUIDField()
    request_fingerprint = models.CharField(max_length=64)
    reference = models.CharField(max_length=64, unique=True)
    provider_reference = models.CharField(max_length=255, blank=True)
    provider_conversation_id = models.CharField(max_length=255, blank=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    response_code = models.CharField(max_length=100, blank=True)
    response_description = models.CharField(max_length=500, blank=True)
    failure_code = models.CharField(max_length=100, blank=True)
    expires_at = models.DateTimeField()
    succeeded_at = models.DateTimeField(blank=True, null=True)
    failed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_intent_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["member", "idempotency_key"],
                name="unique_member_payment_idempotency_key",
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_transaction_id"],
                condition=~Q(provider_transaction_id=""),
                name="unique_provider_transaction_id",
            ),
        ]
        indexes = [
            models.Index(
                fields=["member", "status", "-created_at"],
                name="payment_member_status_idx",
            ),
            models.Index(
                fields=["church", "provider", "status"],
                name="payment_church_provider_idx",
            ),
            models.Index(fields=["expires_at"], name="payment_expiry_idx"),
        ]

    def clean(self):
        """Validate ownership and immutable payment-scope relationships."""

        super().clean()
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Payment amount must be greater than zero."
        if self.currency and self.currency != self.currency.upper():
            errors["currency"] = "Currency must use an uppercase ISO code."
        if (
            self.member_id
            and self.church_id
            and self.member.church_id != self.church_id
        ):
            errors["member"] = "Member must belong to the payment church."
        if (
            self.category_id
            and self.church_id
            and self.category.church_id != self.church_id
        ):
            errors["category"] = "Category must belong to the payment church."
        if (
            self.financial_year_id
            and self.church_id
            and self.financial_year.church_id != self.church_id
        ):
            errors["financial_year"] = (
                "Financial year must belong to the payment church."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        """Return the reference, member, and current status for administration."""

        return f"{self.reference} - {self.member} - {self.status}"


class PaymentAllocation(models.Model):
    """Exact portion of an intent assigned to one contribution period."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    contribution_week = models.ForeignKey(
        ContributionWeek,
        on_delete=models.PROTECT,
        related_name="payment_allocations",
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    contribution = models.OneToOneField(
        Contribution,
        on_delete=models.PROTECT,
        related_name="payment_allocation",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["contribution_week__sunday_date", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_allocation_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["payment_intent", "contribution_week"],
                nulls_distinct=False,
                name="unique_intent_contribution_week",
            ),
        ]

    def clean(self):
        """Validate week scope and any linked posted contribution."""

        super().clean()
        errors = {}
        intent = self.payment_intent if self.payment_intent_id else None
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Allocation amount must be greater than zero."
        if intent:
            is_weekly = intent.category.frequency == "WEEKLY"
            if is_weekly and not self.contribution_week_id:
                errors["contribution_week"] = (
                    "Weekly categories require a contribution week."
                )
            if not is_weekly and self.contribution_week_id:
                errors["contribution_week"] = (
                    "Non-weekly categories cannot select a contribution week."
                )
        if self.contribution_week_id and intent:
            if self.contribution_week.church_id != intent.church_id:
                errors["contribution_week"] = "Week must belong to the payment church."
            elif self.contribution_week.financial_year_id != intent.financial_year_id:
                errors["contribution_week"] = (
                    "Week must belong to the payment financial year."
                )
        if self.contribution_id and intent:
            contribution = self.contribution
            if contribution.member_id != intent.member_id:
                errors["contribution"] = (
                    "Contribution must belong to the payment member."
                )
            elif contribution.category_id != intent.category_id:
                errors["contribution"] = "Contribution must use the payment category."
            elif contribution.church_id != intent.church_id:
                errors["contribution"] = "Contribution must belong to the payment church."
            elif contribution.financial_year_id != intent.financial_year_id:
                errors["contribution"] = (
                    "Contribution must use the payment financial year."
                )
            elif (
                self.contribution_week_id
                and contribution.contribution_week_id != self.contribution_week_id
            ):
                errors["contribution"] = "Contribution must use the allocated week."
            elif contribution.amount != self.amount:
                errors["contribution"] = (
                    "Contribution amount must match the allocation."
                )
            elif contribution.source != "ONLINE_PAYMENT":
                errors["contribution"] = (
                    "Contribution must use the online-payment source."
                )
            elif contribution.status != "POSTED":
                errors["contribution"] = (
                    "Contribution must be posted before it is linked."
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        """Return the intent reference, week, and allocation amount."""

        period = self.contribution_week or "non-weekly"
        return f"{self.payment_intent.reference} - {period} - {self.amount}"


class PaymentAttempt(models.Model):
    """One sanitized provider request and normalized result for an intent."""

    STATUS_CHOICES = [
        ("created", "Created"),
        ("pending_customer_action", "Pending customer action"),
        ("processing", "Processing"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField()
    provider = models.CharField(max_length=40, choices=PAYMENT_PROVIDER_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="created")
    provider_reference = models.CharField(max_length=255, blank=True)
    provider_conversation_id = models.CharField(max_length=255, blank=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    response_code = models.CharField(max_length=100, blank=True)
    response_description = models.CharField(max_length=500, blank=True)
    retryable = models.BooleanField(default=False)
    initiated_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_intent", "attempt_number"]
        constraints = [
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name="payment_attempt_number_positive",
            ),
            models.UniqueConstraint(
                fields=["payment_intent", "attempt_number"],
                name="unique_payment_attempt_number",
            ),
        ]

    def clean(self):
        """Ensure the attempt uses the provider selected by its intent."""

        super().clean()
        if self.payment_intent_id and self.provider != self.payment_intent.provider:
            raise ValidationError(
                {"provider": "Attempt provider must match the payment intent."}
            )

    def __str__(self):
        """Return the intent reference and sequential attempt number."""

        return f"{self.payment_intent.reference} - attempt {self.attempt_number}"


class PaymentWebhookEvent(models.Model):
    """Replay-protected record of a callback received from a payment provider."""

    STATUS_CHOICES = [
        ("received", "Received"),
        ("processed", "Processed"),
        ("ignored", "Ignored"),
        ("failed", "Failed"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider = models.CharField(max_length=40, choices=PAYMENT_PROVIDER_CHOICES)
    payment_intent = models.ForeignKey(
        PaymentIntent,
        on_delete=models.SET_NULL,
        related_name="webhook_events",
        blank=True,
        null=True,
    )
    external_event_id = models.CharField(max_length=255, blank=True)
    payload_hash = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="received")
    request_id = models.CharField(max_length=100, blank=True)
    source_ip = models.GenericIPAddressField(blank=True, null=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_description = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "payload_hash"],
                name="unique_provider_webhook_payload",
            ),
            models.UniqueConstraint(
                fields=["provider", "external_event_id"],
                condition=~Q(external_event_id=""),
                name="unique_provider_webhook_event",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "status", "-received_at"],
                name="webhook_provider_status_idx",
            )
        ]

    def __str__(self):
        """Return the provider, external identity, and processing state."""

        identity = self.external_event_id or self.payload_hash[:12]
        return f"{self.provider} - {identity} - {self.status}"
