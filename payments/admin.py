"""Read-focused administration for payment operations and reconciliation."""

from django.contrib import admin

from .models import (
    PaymentAllocation,
    PaymentAttempt,
    PaymentIntent,
    PaymentWebhookEvent,
)


class PaymentAllocationInline(admin.TabularInline):
    """Show immutable allocation rows inside a payment intent."""

    model = PaymentAllocation
    extra = 0
    can_delete = False
    fields = ("public_id", "contribution_week", "amount", "contribution")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        """Prevent administrators from changing a member's payment allocation."""

        return False


class PaymentAttemptInline(admin.TabularInline):
    """Show sanitized provider-attempt history inside an intent."""

    model = PaymentAttempt
    extra = 0
    can_delete = False
    fields = (
        "attempt_number",
        "provider",
        "status",
        "provider_transaction_id",
        "response_code",
        "retryable",
        "created_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        """Require attempts to be created through the payment service."""

        return False


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    """Expose payment state and references without allowing manual creation."""

    list_display = (
        "reference",
        "member",
        "church",
        "provider",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "provider", "currency", "church", "created_at")
    search_fields = (
        "reference",
        "member__bahasha_number",
        "member__user__full_name",
        "provider_reference",
        "provider_transaction_id",
    )
    date_hierarchy = "created_at"
    inlines = (PaymentAllocationInline, PaymentAttemptInline)
    readonly_fields = tuple(
        field.name for field in PaymentIntent._meta.fields
    )

    def has_add_permission(self, request):
        """Require all intents to pass through validation and idempotency services."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve payment history for audit and reconciliation."""

        return False


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    """Expose callback verification and replay-processing evidence."""

    list_display = (
        "provider",
        "external_event_id",
        "payment_intent",
        "signature_valid",
        "status",
        "received_at",
    )
    list_filter = ("provider", "signature_valid", "status", "received_at")
    search_fields = (
        "external_event_id",
        "payload_hash",
        "payment_intent__reference",
        "request_id",
    )
    date_hierarchy = "received_at"
    readonly_fields = tuple(
        field.name for field in PaymentWebhookEvent._meta.fields
    )

    def has_add_permission(self, request):
        """Require callback records to originate from the webhook service."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve callbacks used for replay protection and audit evidence."""

        return False
