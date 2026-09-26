from django.test import TestCase
from django.urls import reverse

from users.models import User


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="strong-test-password",
            full_name="System Administrator",
            phone_number="255700000001",
            role="ADMIN",
        )

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin", "password": "strong-test-password"},
        )

        self.assertRedirects(response, reverse("web_dashboard"))

    def test_invalid_login_renders_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

# Create your tests here.
