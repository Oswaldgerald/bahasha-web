from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from churches.models import Church
from users.models import User

from .forms import ContributionCategoryForm
from .models import ContributionCategory


class ContributionCategoryWebTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CAT-001",
            church_name="Category Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="CAT-002",
            church_name="Other Category Church",
        )
        self.admin = User.objects.create_user(
            username="category-admin",
            password="Strong-Test-Password-2026",
            full_name="Category Administrator",
            phone_number="255700300001",
            role="ADMIN",
            church=self.church,
        )
        self.category = ContributionCategory.objects.create(
            church=self.church,
            name="Ahadi",
            name_sw="Ahadi",
            key="ahadi",
            code="AHD",
            icon_key="hand-heart",
            theme_color="#A844B7",
        )
        self.other_category = ContributionCategory.objects.create(
            church=self.other_church,
            name="Jengo",
            key="jengo",
            code="JNG",
        )
        self.client.force_login(self.admin)

    def test_category_list_is_scoped_to_administrators_church(self):
        response = self.client.get(reverse("web_categories"))

        self.assertContains(response, self.category.name)
        self.assertNotContains(response, self.other_category.name)

    def test_category_can_configure_mobile_card_and_payment_rules(self):
        response = self.client.post(
            reverse("web_category_create"),
            {
                "church": self.church.id,
                "name": "Mavuno",
                "name_sw": "Mavuno",
                "key": "mavuno",
                "code": "MAV",
                "description": "Harvest contribution",
                "frequency": "SEASONAL",
                "icon_key": "tractor",
                "theme_color": "#27A69A",
                "display_order": 5,
                "suggested_amount": "10000.00",
                "minimum_amount": "1000.00",
                "maximum_amount": "100000.00",
                "is_mobile_visible": "on",
                "allows_member_payment": "on",
                "allows_catch_up": "on",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("web_categories"))
        category = ContributionCategory.objects.get(church=self.church, key="mavuno")
        self.assertEqual(category.icon_key, "tractor")
        self.assertEqual(category.theme_color, "#27A69A")
        self.assertEqual(category.suggested_amount, Decimal("10000.00"))
        self.assertTrue(category.allows_member_payment)
        self.assertTrue(category.allows_catch_up)

    def test_category_form_cannot_assign_another_church(self):
        form = ContributionCategoryForm(
            {
                "church": self.other_church.id,
                "name": "Uwakili",
                "key": "uwakili",
                "frequency": "MONTHLY",
                "icon_key": "scale",
                "theme_color": "#5EAE65",
                "display_order": 3,
                "is_mobile_visible": True,
                "allows_member_payment": True,
                "allows_catch_up": True,
                "is_active": True,
            },
            request_user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("church", form.errors)

    def test_amount_limits_must_be_consistent(self):
        form = ContributionCategoryForm(
            {
                "church": self.church.id,
                "name": "Development",
                "key": "development",
                "frequency": "SEASONAL",
                "icon_key": "building-2",
                "theme_color": "#336699",
                "display_order": 8,
                "minimum_amount": "10000.00",
                "suggested_amount": "5000.00",
                "maximum_amount": "20000.00",
                "is_mobile_visible": True,
                "allows_member_payment": True,
                "allows_catch_up": False,
                "is_active": True,
            },
            request_user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("suggested_amount", form.errors)


class ChurchCategoryDefaultsTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="category-superuser",
            password="Strong-Test-Password-2026",
            email="category-superuser@example.com",
            full_name="Category Superuser",
            phone_number="255700300099",
            role="ADMIN",
        )
        self.client.force_login(self.superuser)

    def test_new_church_receives_default_mobile_categories(self):
        response = self.client.post(
            reverse("web_church_create"),
            {
                "church_code": "NEW-CAT",
                "church_name": "New Category Church",
                "parish": "",
                "district": "",
                "location": "",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("web_churches"))
        church = Church.objects.get(church_code="NEW-CAT")
        self.assertSetEqual(
            set(church.contribution_categories.values_list("key", flat=True)),
            {"ahadi", "jengo", "uwakili", "jumuiya", "mavuno"},
        )
