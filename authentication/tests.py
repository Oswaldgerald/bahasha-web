from django.test import TestCase
from django.urls import reverse

from users.models import User


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api-user",
            password="strong-test-password",
            full_name="API User",
            phone_number="255700000002",
            role="FINANCE_OFFICER",
        )

    def test_login_returns_tokens_and_user(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "api-user",
                "password": "strong-test-password",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("access", payload)
        self.assertIn("refresh", payload)
        self.assertEqual(payload["user"]["username"], "api-user")

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

# Create your tests here.
