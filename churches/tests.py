from django.test import TestCase
from django.urls import reverse

from users.models import User

from .forms import ChurchGroupForm
from .models import Church, ChurchGroup


class ChurchGroupTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="GROUP-001",
            church_name="Group Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="GROUP-002",
            church_name="Other Group Church",
        )
        self.admin = User.objects.create_user(
            username="group-admin",
            password="Strong-Test-Password-2026",
            full_name="Group Administrator",
            phone_number="255700200001",
            role="ADMIN",
            church=self.church,
        )
        self.group = ChurchGroup.objects.create(church=self.church, name="Choir")
        self.other_group = ChurchGroup.objects.create(
            church=self.other_church,
            name="ICT",
        )
        self.client.force_login(self.admin)

    def test_group_list_is_scoped_to_administrators_church(self):
        response = self.client.get(reverse("web_church_groups"))

        self.assertContains(response, self.group.name)
        self.assertNotContains(response, self.other_group.name)

    def test_group_form_rejects_case_insensitive_duplicate_name(self):
        form = ChurchGroupForm(
            {
                "church": self.church.id,
                "name": "choir",
                "description": "Duplicate",
                "is_active": True,
            },
            request_user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_group_form_cannot_assign_another_church(self):
        form = ChurchGroupForm(
            {
                "church": self.other_church.id,
                "name": "Youth",
                "description": "",
                "is_active": True,
            },
            request_user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("church", form.errors)
