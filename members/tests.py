from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from churches.models import Church
from jumuiya.models import Jumuiya
from users.models import User
from web.forms import MemberCreateForm

from .models import Member
from .services import approve_member, create_member, reject_member


class MemberServiceTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="MEM-001",
            church_name="Member Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="MEM-002",
            church_name="Other Test Church",
        )
        self.jumuiya = Jumuiya.objects.create(
            church=self.church,
            name="St Monica",
        )
        self.other_jumuiya = Jumuiya.objects.create(
            church=self.other_church,
            name="St Peter",
        )

    def member_data(self, **overrides):
        data = {
            "username": "new-member",
            "full_name": "New Member",
            "phone_number": "255700100001",
            "email": "member@example.com",
            "password": "Strong-Test-Password-2026",
            "church": self.church,
            "jumuiya": self.jumuiya,
            "bahasha_number": "MEM-B-001",
            "gender": "FEMALE",
            "demographics": "Adult",
            "approval_status": "PENDING",
        }
        data.update(overrides)
        return data

    def test_create_member_rolls_back_user_when_member_is_invalid(self):
        with self.assertRaises(ValidationError):
            create_member(self.member_data(jumuiya=self.other_jumuiya))

        self.assertFalse(User.objects.filter(username="new-member").exists())
        self.assertFalse(Member.objects.filter(bahasha_number="MEM-B-001").exists())

    def test_approval_and_rejection_keep_login_state_in_sync(self):
        member = create_member(self.member_data())
        self.assertFalse(member.is_active)
        self.assertFalse(member.user.is_active)

        approve_member(member)
        member.refresh_from_db()
        member.user.refresh_from_db()
        self.assertEqual(member.approval_status, "APPROVED")
        self.assertTrue(member.is_active)
        self.assertTrue(member.user.is_active)
        self.assertIsNotNone(member.approved_at)

        reject_member(member)
        member.refresh_from_db()
        member.user.refresh_from_db()
        self.assertEqual(member.approval_status, "REJECTED")
        self.assertFalse(member.is_active)
        self.assertFalse(member.user.is_active)
        self.assertIsNone(member.approved_at)


class MemberFormTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="FORM-001",
            church_name="Form Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="FORM-002",
            church_name="Other Form Church",
        )
        self.jumuiya = Jumuiya.objects.create(church=self.church, name="St Anne")
        self.other_jumuiya = Jumuiya.objects.create(
            church=self.other_church,
            name="St Mark",
        )
        self.admin = User.objects.create_user(
            username="member-admin",
            password="Strong-Test-Password-2026",
            full_name="Member Administrator",
            phone_number="255700100010",
            role="ADMIN",
            church=self.church,
        )

    def form_data(self, **overrides):
        data = {
            "username": "form-member",
            "full_name": "Form Member",
            "phone_number": "255700100011",
            "email": "form-member@example.com",
            "password": "Strong-Test-Password-2026",
            "church": str(self.church.id),
            "jumuiya": str(self.jumuiya.id),
            "bahasha_number": "form-b-001",
            "gender": "MALE",
            "demographics": "Youth",
            "approval_status": "APPROVED",
        }
        data.update(overrides)
        return data

    def test_create_form_scopes_church_and_jumuiya_to_administrator(self):
        form = MemberCreateForm(request_user=self.admin)

        self.assertQuerySetEqual(form.fields["church"].queryset, [self.church])
        self.assertQuerySetEqual(form.fields["jumuiya"].queryset, [self.jumuiya])

    def test_create_form_rejects_cross_church_jumuiya(self):
        form = MemberCreateForm(
            self.form_data(jumuiya=str(self.other_jumuiya.id)),
            request_user=self.admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("jumuiya", form.errors)

    def test_create_form_normalizes_bahasha_number(self):
        form = MemberCreateForm(self.form_data(), request_user=self.admin)

        self.assertTrue(form.is_valid(), form.errors)
        member = form.save()
        self.assertEqual(member.bahasha_number, "FORM-B-001")
        self.assertIsNotNone(member.approved_at)
        self.assertLessEqual(member.approved_at, timezone.now())


class MemberViewTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="VIEW-001",
            church_name="View Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="VIEW-002",
            church_name="Other View Church",
        )
        self.jumuiya = Jumuiya.objects.create(church=self.church, name="St Luke")
        self.other_jumuiya = Jumuiya.objects.create(
            church=self.other_church,
            name="St Paul",
        )
        self.admin = User.objects.create_user(
            username="view-admin",
            password="Strong-Test-Password-2026",
            full_name="View Administrator",
            phone_number="255700100020",
            role="ADMIN",
            church=self.church,
        )
        other_user = User.objects.create_user(
            username="other-member",
            password="Strong-Test-Password-2026",
            full_name="Other Church Member",
            phone_number="255700100021",
            role="MEMBER",
            church=self.other_church,
        )
        self.other_member = Member.objects.create(
            user=other_user,
            church=self.other_church,
            jumuiya=self.other_jumuiya,
            bahasha_number="VIEW-B-001",
        )
        self.client.force_login(self.admin)

    def test_member_pages_do_not_expose_another_church(self):
        list_response = self.client.get(reverse("web_members"))
        detail_response = self.client.get(
            reverse("web_member_detail", args=[self.other_member.id])
        )

        self.assertNotContains(list_response, self.other_member.user.full_name)
        self.assertEqual(detail_response.status_code, 404)

    def test_jumuiya_options_are_limited_to_administrators_church(self):
        own_response = self.client.get(
            reverse("web_member_jumuiya_options"),
            {"church_id": self.church.id},
        )
        other_response = self.client.get(
            reverse("web_member_jumuiya_options"),
            {"church_id": self.other_church.id},
        )

        self.assertEqual(
            own_response.json(),
            {"options": [{"value": self.jumuiya.id, "label": self.jumuiya.name}]},
        )
        self.assertEqual(other_response.json(), {"options": []})
