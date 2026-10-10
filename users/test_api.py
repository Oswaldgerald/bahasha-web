import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from financial_years.models import FinancialYear
from members.models import Member
from notifications.models import MobileDevice, Notification, NotificationReceipt
from users.models import ApiTokenSession, User
from users.tokens import hash_token


class MemberApiTests(TestCase):
    password = "Strong-Test-Password-982!"

    @classmethod
    def setUpTestData(cls):
        cls.church = Church.objects.create(
            church_code="API-001",
            church_name="API Test Church",
        )
        cls.user = User.objects.create_user(
            username="api-member",
            password=cls.password,
            full_name="API Member",
            phone_number="+255700000001",
            role="MEMBER",
            church=cls.church,
            email="member@example.test",
        )
        cls.member = Member.objects.create(
            user=cls.user,
            church=cls.church,
            bahasha_number="API-0001",
            approval_status="APPROVED",
        )
        today = timezone.localdate()
        cls.year = FinancialYear.objects.create(
            church=cls.church,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
            is_active=True,
        )
        cls.current_week = ContributionWeek.objects.create(
            church=cls.church,
            financial_year=cls.year,
            week_number=2,
            sunday_date=today,
            is_active=True,
        )
        cls.missing_week = ContributionWeek.objects.create(
            church=cls.church,
            financial_year=cls.year,
            week_number=1,
            sunday_date=today - timedelta(days=7),
        )
        cls.category = ContributionCategory.objects.create(
            church=cls.church,
            name="Ahadi",
            name_sw="Ahadi",
            key="ahadi",
            frequency="WEEKLY",
            display_order=1,
            is_mobile_visible=True,
            allows_member_payment=True,
            allows_catch_up=True,
        )

    def post_json(self, path, payload, *, token=None):
        headers = {}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def login(self, identifier="api-member"):
        response = self.post_json(
            "/api/v1/auth/token",
            {
                "identifier": identifier,
                "password": self.password,
                "device": {
                    "installation_id": str(uuid.uuid4()),
                    "platform": "android",
                    "app_version": "1.0.0",
                    "device_name": "Test phone",
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def auth_get(self, path, token):
        return self.client.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_health_and_member_login(self):
        health = self.client.get("/api/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.headers["X-Request-ID"])

        tokens = self.login(identifier="0700000001")
        session = ApiTokenSession.objects.get(user=self.user)
        self.assertNotEqual(session.access_token_hash, tokens["access_token"])
        self.assertEqual(session.access_token_hash, hash_token(tokens["access_token"]))

        profile = self.auth_get("/api/v1/me", tokens["access_token"])
        self.assertEqual(profile.status_code, 200, profile.content)
        self.assertEqual(profile.json()["bahasha_number"], "API-0001")

    def test_unapproved_member_cannot_login(self):
        self.member.approval_status = "PENDING"
        self.member.save(update_fields=["approval_status", "updated_at"])
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
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "MEMBER_NOT_APPROVED")

    def test_refresh_rotation_and_reuse_revoke_token_family(self):
        initial = self.login()
        refreshed = self.post_json(
            "/api/v1/auth/token/refresh",
            {"refresh_token": initial["refresh_token"]},
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.content)

        reuse = self.post_json(
            "/api/v1/auth/token/refresh",
            {"refresh_token": initial["refresh_token"]},
        )
        self.assertEqual(reuse.status_code, 401)
        self.assertEqual(reuse.json()["error"]["code"], "TOKEN_REVOKED")

        new_access = refreshed.json()["access_token"]
        rejected = self.auth_get("/api/v1/me", new_access)
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(rejected.json()["error"]["code"], "TOKEN_REVOKED")

    def test_password_change_revokes_active_sessions(self):
        tokens = self.login()
        user = User.objects.get(pk=self.user.pk)
        user.set_password("Another-Strong-Password-735!")
        user.save(update_fields=["password"])
        response = self.auth_get("/api/v1/me", tokens["access_token"])
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "TOKEN_REVOKED")

    def test_logout_is_idempotent_for_the_same_token(self):
        tokens = self.login()
        first = self.post_json(
            "/api/v1/auth/logout",
            {},
            token=tokens["access_token"],
        )
        second = self.post_json(
            "/api/v1/auth/logout",
            {},
            token=tokens["access_token"],
        )
        self.assertEqual(first.status_code, 204, first.content)
        self.assertEqual(second.status_code, 204, second.content)

    def test_bootstrap_uses_configurable_categories_and_missing_weeks(self):
        tokens = self.login()
        response = self.auth_get("/api/v1/bootstrap", tokens["access_token"])
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["categories"][0]["key"], "ahadi")
        self.assertEqual(payload["categories"][0]["missing_weeks_count"], 2)
        self.assertFalse(payload["capabilities"]["payments_enabled"])

    def test_week_schedule_places_active_week_first(self):
        ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.year,
            week_number=3,
            sunday_date=timezone.localdate() + timedelta(days=7),
        )
        tokens = self.login()
        response = self.auth_get(
            f"/api/v1/contribution-categories/{self.category.public_id}/weeks",
            tokens["access_token"],
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["items"][0]["week_number"], 2)

    def test_contribution_detail_is_scoped_to_authenticated_member(self):
        other_user = User.objects.create_user(
            username="other-member",
            password=self.password,
            full_name="Other Member",
            phone_number="+255700000002",
            role="MEMBER",
            church=self.church,
        )
        other_member = Member.objects.create(
            user=other_user,
            church=self.church,
            bahasha_number="API-0002",
            approval_status="APPROVED",
        )
        contribution = Contribution.objects.create(
            church=self.church,
            member=other_member,
            bahasha_number=other_member.bahasha_number,
            financial_year=self.year,
            contribution_week=self.current_week,
            category=self.category,
            amount=Decimal("1000.00"),
            contribution_date=self.current_week.sunday_date,
            source="MANUAL_ENTRY",
            status="POSTED",
            reference_number="API-OTHER-001",
        )
        tokens = self.login()
        response = self.auth_get(
            f"/api/v1/contributions/{contribution.public_id}",
            tokens["access_token"],
        )
        self.assertEqual(response.status_code, 404)

    def test_notifications_read_state_and_device_registration(self):
        visible = Notification.objects.create(
            church=self.church,
            title="Visible announcement",
            message="Welcome",
            notification_type="CHURCH_ANNOUNCEMENT",
            target_role=None,
            status="SENT",
            sent_at=timezone.now(),
        )
        Notification.objects.create(
            church=self.church,
            title="Staff only",
            message="Internal",
            notification_type="SYSTEM_MESSAGE",
            target_role="ADMIN",
            status="SENT",
            sent_at=timezone.now(),
        )
        tokens = self.login()
        listed = self.auth_get("/api/v1/notifications", tokens["access_token"])
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual([item["title"] for item in listed.json()["items"]], ["Visible announcement"])

        read = self.post_json(
            f"/api/v1/notifications/{visible.public_id}/read",
            {},
            token=tokens["access_token"],
        )
        self.assertEqual(read.status_code, 204, read.content)
        self.assertTrue(
            NotificationReceipt.objects.filter(
                notification=visible,
                user=self.user,
                read_at__isnull=False,
            ).exists()
        )

        installation_id = uuid.uuid4()
        device = self.post_json(
            "/api/v1/devices",
            {
                "installation_id": str(installation_id),
                "platform": "android",
                "push_token": "push-token",
                "app_version": "1.0.0",
            },
            token=tokens["access_token"],
        )
        self.assertEqual(device.status_code, 201, device.content)
        self.assertTrue(
            MobileDevice.objects.filter(
                user=self.user,
                installation_id=installation_id,
                is_active=True,
            ).exists()
        )

    def test_payment_boundary_is_explicitly_disabled(self):
        tokens = self.login()
        methods = self.auth_get("/api/v1/payment-methods", tokens["access_token"])
        self.assertEqual(methods.status_code, 200)
        self.assertEqual(methods.json(), {"items": []})

        create = self.post_json(
            "/api/v1/payment-intents",
            {"amount": "1000.00"},
            token=tokens["access_token"],
        )
        self.assertEqual(create.status_code, 503)
        self.assertEqual(create.json()["error"]["code"], "PAYMENTS_UNAVAILABLE")
