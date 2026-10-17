"""Database behavior tests for provider-neutral payment persistence."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from audit_logs.models import AuditLog
from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User

from .models import PaymentIntent, PaymentWebhookEvent
from .providers import (
    PaymentProviderError,
    PaymentProviderResult,
    PaymentProviderStatus,
)
from .services import (
    PaymentAllocationInput,
    PaymentServiceError,
    create_payment_attempt,
    create_payment_intent,
    initiate_payment_intent,
    record_webhook_event,
    transition_payment_intent,
)


class RecordingProvider:
    """Return a configured result or error while recording initiation input."""

    key = "airtel_money"

    def __init__(self, *, result=None, error=None):
        """Store the deterministic provider outcome used by a test."""

        self.result = result
        self.error = error
        self.calls = []

    def initiate(self, payment):
        """Record the provider-neutral request and return the configured outcome."""

        self.calls.append(payment)
        if self.error:
            raise self.error
        return self.result


class PaymentPersistenceTests(TestCase):
    """Exercise intent ownership, idempotency, allocations, and callback replay."""

    def setUp(self):
        """Create one active member and payment-eligible accounting period."""

        today = timezone.localdate()
        self.church = Church.objects.create(
            church_code="PAY",
            church_name="Payment Test Church",
        )
        self.user = User.objects.create_user(
            username="payment-member",
            password="StrongPassword123!",
            full_name="Payment Member",
            phone_number="+255700000001",
            role="MEMBER",
            church=self.church,
        )
        self.member = Member.objects.create(
            user=self.user,
            church=self.church,
            bahasha_number="PAY-001",
            approval_status="APPROVED",
            is_active=True,
        )
        self.financial_year = FinancialYear.objects.create(
            church=self.church,
            year=today.year,
            start_date=today - timedelta(days=180),
            end_date=today + timedelta(days=180),
            is_active=True,
        )
        self.category = ContributionCategory.objects.create(
            church=self.church,
            name="Ahadi",
            name_sw="Ahadi",
            key="ahadi",
            frequency="WEEKLY",
            allows_member_payment=True,
            allows_catch_up=True,
        )
        self.week_one = ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=1,
            sunday_date=today - timedelta(days=7),
        )
        self.week_two = ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=2,
            sunday_date=today,
            is_active=True,
        )

    def create_intent(self, *, key=None, allocations=None, category=None):
        """Create an intent through the production service using test defaults."""

        return create_payment_intent(
            member=self.member,
            category=category or self.category,
            financial_year=self.financial_year,
            provider="airtel_money",
            payer_phone_number="0700 000 001",
            idempotency_key=key or uuid.uuid4(),
            allocations=allocations
            or [PaymentAllocationInput(Decimal("5000.00"), self.week_two)],
        )

    def test_intent_persists_derived_total_and_normalized_phone(self):
        """Store one atomic intent with its exact weekly allocations."""

        intent, created = self.create_intent(
            allocations=[
                PaymentAllocationInput(Decimal("3000.00"), self.week_one),
                PaymentAllocationInput(Decimal("5000.00"), self.week_two),
            ]
        )

        self.assertTrue(created)
        self.assertEqual(intent.amount, Decimal("8000.00"))
        self.assertEqual(intent.payer_phone_number, "255700000001")
        self.assertEqual(intent.status, "created")
        self.assertTrue(intent.reference.startswith("BHS-"))
        self.assertEqual(intent.allocations.count(), 2)

    def test_same_key_and_canonical_body_returns_original_intent(self):
        """Treat allocation ordering differences as the same logical request."""

        key = uuid.uuid4()
        original, original_created = self.create_intent(
            key=key,
            allocations=[
                PaymentAllocationInput(Decimal("3000.00"), self.week_one),
                PaymentAllocationInput(Decimal("5000.00"), self.week_two),
            ],
        )
        replay, replay_created = self.create_intent(
            key=key,
            allocations=[
                PaymentAllocationInput(Decimal("5000.00"), self.week_two),
                PaymentAllocationInput(Decimal("3000.00"), self.week_one),
            ],
        )

        self.assertTrue(original_created)
        self.assertFalse(replay_created)
        self.assertEqual(replay.pk, original.pk)
        self.assertEqual(PaymentIntent.objects.count(), 1)

    def test_same_key_with_changed_amount_is_rejected(self):
        """Prevent an idempotency key from authorizing a modified payment."""

        key = uuid.uuid4()
        self.create_intent(key=key)

        with self.assertRaises(PaymentServiceError) as raised:
            self.create_intent(
                key=key,
                allocations=[PaymentAllocationInput(Decimal("6000.00"), self.week_two)],
            )

        self.assertEqual(raised.exception.code, "IDEMPOTENCY_CONFLICT")
        self.assertEqual(PaymentIntent.objects.count(), 1)

    def test_cross_church_week_is_rejected_without_partial_records(self):
        """Reject foreign periods before an intent or allocation is persisted."""

        other_church = Church.objects.create(
            church_code="OTHER",
            church_name="Other Church",
        )
        other_year = FinancialYear.objects.create(
            church=other_church,
            year=self.financial_year.year,
            start_date=self.financial_year.start_date,
            end_date=self.financial_year.end_date,
            is_active=True,
        )
        other_week = ContributionWeek.objects.create(
            church=other_church,
            financial_year=other_year,
            week_number=1,
            sunday_date=timezone.localdate(),
            is_active=True,
        )

        with self.assertRaises(PaymentServiceError) as raised:
            self.create_intent(
                allocations=[PaymentAllocationInput(Decimal("5000.00"), other_week)]
            )

        self.assertEqual(raised.exception.code, "CONTRIBUTION_WEEK_NOT_FOUND")
        self.assertEqual(PaymentIntent.objects.count(), 0)

    def test_category_without_catch_up_rejects_an_earlier_week(self):
        """Allow categories to disable member payments against past weeks."""

        self.category.allows_catch_up = False
        self.category.save(update_fields=["allows_catch_up", "updated_at"])

        with self.assertRaises(PaymentServiceError) as raised:
            self.create_intent(
                allocations=[PaymentAllocationInput(Decimal("5000.00"), self.week_one)]
            )

        self.assertEqual(raised.exception.code, "CATEGORY_CATCH_UP_DISABLED")

    def test_non_weekly_category_uses_one_periodless_allocation(self):
        """Persist annual or seasonal payments without a synthetic week."""

        annual = ContributionCategory.objects.create(
            church=self.church,
            name="Mavuno",
            key="mavuno",
            frequency="ANNUAL",
            allows_member_payment=True,
        )

        intent, created = self.create_intent(
            category=annual,
            allocations=[PaymentAllocationInput(Decimal("15000.00"))],
        )

        self.assertTrue(created)
        self.assertIsNone(intent.allocations.get().contribution_week)

    def test_payment_attempt_numbers_are_sequential(self):
        """Serialize attempt numbering beneath one locked payment intent."""

        intent, _created = self.create_intent()

        first = create_payment_attempt(intent)
        second = create_payment_attempt(intent)

        self.assertEqual(first.attempt_number, 1)
        self.assertEqual(second.attempt_number, 2)
        self.assertEqual(first.provider, intent.provider)

    def test_duplicate_webhook_payload_is_recorded_once(self):
        """Return the original callback record when a provider retries delivery."""

        raw_body = b'{"event_id":"airtel-event-1","status":"SUCCESS"}'
        payload = {"event_id": "airtel-event-1", "status": "SUCCESS"}

        original, original_created = record_webhook_event(
            provider="airtel_money",
            raw_body=raw_body,
            payload=payload,
            signature_valid=True,
            external_event_id="airtel-event-1",
        )
        replay, replay_created = record_webhook_event(
            provider="airtel_money",
            raw_body=raw_body,
            payload=payload,
            signature_valid=True,
            external_event_id="airtel-event-1",
        )

        self.assertTrue(original_created)
        self.assertFalse(replay_created)
        self.assertEqual(replay.pk, original.pk)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)

    def test_provider_initiation_persists_prompt_state_and_references(self):
        """Move a fresh intent to customer action without claiming settlement."""

        intent, _created = self.create_intent()
        provider = RecordingProvider(
            result=PaymentProviderResult(
                status=PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
                provider_reference="airtel-reference",
                conversation_id="airtel-conversation",
                transaction_id="airtel-transaction",
                response_code="ACCEPTED",
                response_description="Prompt sent",
            )
        )

        updated_intent, attempt = initiate_payment_intent(
            intent,
            provider_adapter=provider,
        )

        self.assertEqual(updated_intent.status, "pending_customer_action")
        self.assertEqual(updated_intent.provider_transaction_id, "airtel-transaction")
        self.assertEqual(attempt.status, "pending_customer_action")
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(provider.calls[0].amount, intent.amount)
        self.assertEqual(provider.calls[0].reference, intent.reference)
        self.assertEqual(
            AuditLog.objects.filter(
                action="PAYMENT_STATUS_CHANGED",
                entity_id=str(intent.public_id),
            ).count(),
            2,
        )

    def test_initiation_success_is_kept_processing_until_verified(self):
        """Never interpret an initiation success response as settled money."""

        intent, _created = self.create_intent()
        provider = RecordingProvider(
            result=PaymentProviderResult(
                status=PaymentProviderStatus.SUCCEEDED,
                transaction_id="provider-accepted-transaction",
            )
        )

        updated_intent, attempt = initiate_payment_intent(
            intent,
            provider_adapter=provider,
        )

        self.assertEqual(updated_intent.status, "processing")
        self.assertEqual(attempt.status, "processing")
        self.assertIsNone(updated_intent.succeeded_at)

    def test_non_retryable_provider_error_fails_intent_and_attempt(self):
        """Persist a safe terminal failure when the provider rejects initiation."""

        intent, _created = self.create_intent()
        provider = RecordingProvider(
            error=PaymentProviderError(
                "AIRTEL_CONFIGURATION_ERROR",
                "Airtel Money rejected the request.",
                retryable=False,
            )
        )

        with self.assertRaises(PaymentProviderError):
            initiate_payment_intent(intent, provider_adapter=provider)

        intent.refresh_from_db()
        attempt = intent.attempts.get()
        self.assertEqual(intent.status, "failed")
        self.assertEqual(intent.failure_code, "AIRTEL_CONFIGURATION_ERROR")
        self.assertEqual(attempt.status, "failed")
        self.assertFalse(attempt.retryable)

    def test_retryable_provider_error_remains_processing_for_reconciliation(self):
        """Keep an ambiguous network failure nonterminal to avoid double charging."""

        intent, _created = self.create_intent()
        provider = RecordingProvider(
            error=PaymentProviderError(
                "AIRTEL_UNAVAILABLE",
                "Airtel Money could not be reached.",
                retryable=True,
            )
        )

        with self.assertRaises(PaymentProviderError):
            initiate_payment_intent(intent, provider_adapter=provider)

        intent.refresh_from_db()
        attempt = intent.attempts.get()
        self.assertEqual(intent.status, "processing")
        self.assertEqual(attempt.status, "processing")
        self.assertTrue(attempt.retryable)

    def test_expired_intent_never_contacts_provider(self):
        """Expire a stale request under lock before creating a provider attempt."""

        intent, _created = self.create_intent()
        intent.expires_at = timezone.now() - timedelta(seconds=1)
        intent.save(update_fields=["expires_at", "updated_at"])
        provider = RecordingProvider(
            result=PaymentProviderResult(
                status=PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
            )
        )

        with self.assertRaises(PaymentServiceError) as raised:
            initiate_payment_intent(intent, provider_adapter=provider)

        intent.refresh_from_db()
        self.assertEqual(raised.exception.code, "PAYMENT_EXPIRED")
        self.assertEqual(intent.status, "expired")
        self.assertEqual(provider.calls, [])
        self.assertFalse(intent.attempts.exists())

    def test_second_initiation_is_rejected_without_another_provider_call(self):
        """Prevent duplicate handset prompts for an already-started intent."""

        intent, _created = self.create_intent()
        first_provider = RecordingProvider(
            result=PaymentProviderResult(
                status=PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
            )
        )
        initiate_payment_intent(intent, provider_adapter=first_provider)
        second_provider = RecordingProvider(
            result=PaymentProviderResult(
                status=PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
            )
        )

        with self.assertRaises(PaymentServiceError) as raised:
            initiate_payment_intent(intent, provider_adapter=second_provider)

        self.assertEqual(raised.exception.code, "PAYMENT_ALREADY_STARTED")
        self.assertEqual(second_provider.calls, [])
        self.assertEqual(intent.attempts.count(), 1)

    def test_unverified_or_illegal_status_transitions_are_rejected(self):
        """Protect settlement and terminal states from unsafe transitions."""

        intent, _created = self.create_intent()

        with self.assertRaises(PaymentServiceError) as unverified:
            transition_payment_intent(intent, "succeeded")
        self.assertEqual(
            unverified.exception.code,
            "PAYMENT_SETTLEMENT_UNVERIFIED",
        )

        failed = transition_payment_intent(intent, "failed")
        with self.assertRaises(PaymentServiceError) as terminal:
            transition_payment_intent(failed, "processing")
        self.assertEqual(terminal.exception.code, "PAYMENT_STATUS_CONFLICT")
