"""End-to-end API tests for the JSON-backed mobile payment simulator."""

import json
import uuid
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from financial_years.models import FinancialYear
from members.models import Member
from payments.models import PaymentIntent
from users.models import User


@override_settings(
    PAYMENTS_ENABLED=True,
    PAYMENT_PROVIDER_MODE="mock",
    PAYMENT_MOCK_SCENARIO="success",
)
class MockPaymentApiTests(TestCase):
    """Exercise the same authenticated contract consumed by the Flutter app."""

    password = "Strong-Test-Password-982!"

    @classmethod
    def setUpTestData(cls):
        """Create one approved member and one payable weekly category."""

        cls.church = Church.objects.create(
            church_code="MOCK-PAY",
            church_name="Mock Payment Church",
        )
        cls.user = User.objects.create_user(
            username="mock-payment-member",
            password=cls.password,
            full_name="Mock Payment Member",
            phone_number="+255700000011",
            role="MEMBER",
            church=cls.church,
        )
        cls.member = Member.objects.create(
            user=cls.user,
            church=cls.church,
            bahasha_number="MOCK-001",
            approval_status="APPROVED",
            is_active=True,
        )
        today = timezone.localdate()
        cls.year = FinancialYear.objects.create(
            church=cls.church,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
            is_active=True,
        )
        cls.week = ContributionWeek.objects.create(
            church=cls.church,
            financial_year=cls.year,
            week_number=1,
            sunday_date=today - timedelta(days=7),
            is_active=True,
        )
        cls.category = ContributionCategory.objects.create(
            church=cls.church,
            name="Ahadi",
            name_sw="Ahadi",
            key="ahadi",
            frequency="WEEKLY",
            is_mobile_visible=True,
            allows_member_payment=True,
            allows_catch_up=True,
        )

    def post_json(self, path, payload, *, token=None, idempotency_key=None):
        """Send JSON with optional member authorization and idempotency headers."""

        headers = {}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        if idempotency_key:
            headers["HTTP_IDEMPOTENCY_KEY"] = str(idempotency_key)
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def login(self):
        """Issue one member access token through the production auth endpoint."""

        response = self.post_json(
            "/api/v1/auth/token",
            {
                "identifier": self.user.username,
                "password": self.password,
                "device": {
                    "installation_id": str(uuid.uuid4()),
                    "platform": "android",
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["access_token"]

    def auth_get(self, path, token):
        """Request a member endpoint using one access token."""

        return self.client.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")

    def payment_payload(self):
        """Build one valid weekly payment body."""

        return {
            "category_id": str(self.category.public_id),
            "financial_year_id": str(self.year.public_id),
            "payment_method": "mobile_money",
            "provider": "vodacom_m_pesa",
            "payer_phone_number": "0700000011",
            "allocations": [
                {
                    "contribution_week_id": str(self.week.public_id),
                    "amount": "5000.00",
                }
            ],
        }

    def create_intent(self, token, *, key=None):
        """Create one simulated payment through the public API."""

        return self.post_json(
            "/api/v1/payment-intents",
            self.payment_payload(),
            token=token,
            idempotency_key=key or uuid.uuid4(),
        )

    def test_methods_and_bootstrap_advertise_mock_payments(self):
        """Expose payment capability and all simulated Tanzania providers."""

        token = self.login()
        methods = self.auth_get("/api/v1/payment-methods", token)
        bootstrap = self.auth_get("/api/v1/bootstrap", token)

        self.assertEqual(methods.status_code, 200, methods.content)
        self.assertEqual(
            methods.json()["items"][0]["providers"],
            ["vodacom_m_pesa", "airtel_money", "mixx_by_yas"],
        )
        self.assertTrue(bootstrap.json()["capabilities"]["payments_enabled"])

    def test_create_then_poll_posts_one_real_contribution(self):
        """Settle a mock prompt and atomically post its weekly allocation."""

        token = self.login()
        created = self.create_intent(token)
        self.assertEqual(created.status_code, 202, created.content)
        self.assertEqual(created.json()["status"], "pending_customer_action")
        intent_id = created.json()["id"]

        settled = self.auth_get(f"/api/v1/payment-intents/{intent_id}", token)
        repeated = self.auth_get(f"/api/v1/payment-intents/{intent_id}", token)

        self.assertEqual(settled.status_code, 200, settled.content)
        self.assertEqual(settled.json()["status"], "succeeded")
        self.assertEqual(len(settled.json()["contribution_ids"]), 1)
        self.assertEqual(repeated.json()["status"], "succeeded")
        self.assertEqual(Contribution.objects.count(), 1)
        contribution = Contribution.objects.get()
        self.assertEqual(contribution.source, "ONLINE_PAYMENT")
        self.assertEqual(contribution.amount, 5000)
        intent = PaymentIntent.objects.get(public_id=intent_id)
        self.assertEqual(intent.allocations.get().contribution, contribution)

    def test_idempotent_replay_does_not_send_or_post_twice(self):
        """Return the original intent for a repeated logical submission."""

        token = self.login()
        key = uuid.uuid4()
        first = self.create_intent(token, key=key)
        second = self.create_intent(token, key=key)

        self.assertEqual(first.status_code, 202, first.content)
        self.assertEqual(second.status_code, 202, second.content)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(PaymentIntent.objects.count(), 1)
        self.assertEqual(PaymentIntent.objects.get().attempts.count(), 1)

    def test_new_payment_for_a_posted_week_is_rejected(self):
        """Prevent a second mobile payment from targeting an already paid week."""

        token = self.login()
        created = self.create_intent(token)
        self.auth_get(
            f"/api/v1/payment-intents/{created.json()['id']}",
            token,
        )

        duplicate = self.create_intent(token)

        self.assertEqual(duplicate.status_code, 422, duplicate.content)
        self.assertEqual(
            duplicate.json()["error"]["code"],
            "PAYMENT_WEEK_ALREADY_PAID",
        )
        self.assertEqual(Contribution.objects.count(), 1)
        self.assertEqual(PaymentIntent.objects.count(), 1)

    def test_missing_idempotency_header_is_rejected(self):
        """Require clients to identify a logical payment submission."""

        token = self.login()
        response = self.post_json(
            "/api/v1/payment-intents",
            self.payment_payload(),
            token=token,
        )

        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(PaymentIntent.objects.count(), 0)

    @override_settings(PAYMENTS_ENABLED=False)
    def test_disabled_flag_hides_payment_methods(self):
        """Hide providers when the production payment kill switch is active."""

        token = self.login()
        response = self.auth_get("/api/v1/payment-methods", token)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"items": []})
