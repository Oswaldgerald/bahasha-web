from django.test import TestCase
from django.urls import reverse

from users.models import User


class HealthCheckTests(TestCase):
    def test_health_check_confirms_database_is_available(self):
        response = self.client.get(reverse("health_check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "healthy", "database": "available"},
        )


class AdminInterfaceTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin-interface",
            password="strong-test-password",
            full_name="Admin Interface",
            phone_number="255700009999",
            role="ADMIN",
        )
        self.client.force_login(self.superuser)

    def test_admin_uses_bahasha_branding_and_workspace_navigation(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bahasha")
        self.assertContains(response, "Administration")
        self.assertContains(response, reverse("web_dashboard"))
        self.assertContains(response, "css/admin.")
        self.assertContains(response, "js/admin.")
