"""Database behavior tests for provider-neutral payment persistence."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User

from .models import PaymentIntent, PaymentWebhookEvent
from .services import (
    PaymentAllocationInput,
    PaymentServiceError,
    create_payment_attempt,
    create_payment_intent,
    record_webhook_event,
)


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
