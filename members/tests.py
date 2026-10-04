from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from churches.models import Church, ChurchGroup
from jumuiya.models import Jumuiya
from users.models import User

from .forms import MemberCreateForm
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
        self.choir = ChurchGroup.objects.create(church=self.church, name="Choir")
        self.other_group = ChurchGroup.objects.create(
            church=self.other_church,
            name="ICT",
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
            "marital_status": "MARRIED",
            "church_groups": [self.choir],
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

    def test_create_member_rejects_group_from_another_church(self):
        with self.assertRaises(ValidationError):
            create_member(self.member_data(church_groups=[self.other_group]))

        self.assertFalse(User.objects.filter(username="new-member").exists())

    def test_create_member_saves_marital_status_and_groups(self):
        member = create_member(self.member_data())

        self.assertEqual(member.marital_status, "MARRIED")
        self.assertQuerySetEqual(member.church_groups.all(), [self.choir])

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
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)
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
        self.choir = ChurchGroup.objects.create(church=self.church, name="Choir")
        self.other_group = ChurchGroup.objects.create(
            church=self.other_church,
            name="ICT",
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
            "phone_country_code": "255",
            "phone_number": "0700100011",
            "email": "form-member@example.com",
            "password": "Strong-Test-Password-2026",
            "church": str(self.church.id),
            "jumuiya": str(self.jumuiya.id),
            "bahasha_number": "form-b-001",
            "gender": "MALE",
            "marital_status": "SINGLE",
            "church_groups": [str(self.choir.id)],
            "demographics": "Youth",
            "approval_status": "APPROVED",
        }
        data.update(overrides)
        return data

    @staticmethod
    def profile_picture():
        image_data = BytesIO()
        Image.new("RGB", (64, 64), color=(45, 27, 105)).save(image_data, "PNG")
        return SimpleUploadedFile(
            "member.png",
            image_data.getvalue(),
            content_type="image/png",
        )

    def test_create_form_scopes_church_and_jumuiya_to_administrator(self):
        form = MemberCreateForm(request_user=self.admin)

        self.assertQuerySetEqual(form.fields["church"].queryset, [self.church])
        self.assertQuerySetEqual(form.fields["jumuiya"].queryset, [self.jumuiya])
        self.assertQuerySetEqual(form.fields["church_groups"].queryset, [self.choir])
        self.assertEqual(
            form.fields["phone_country_code"].choices[0],
            ("255", "Tanzania (+255)"),
        )

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

    def test_create_form_saves_photo_and_normalizes_phone_number(self):
        form = MemberCreateForm(
            self.form_data(),
            {"profile_picture": self.profile_picture()},
            request_user=self.admin,
        )

        self.assertTrue(form.is_valid(), form.errors)
        member = form.save()
        self.assertEqual(member.user.phone_number, "+255700100011")
        self.assertTrue(member.user.profile_picture.name.startswith("profile_pictures/"))


class MemberViewTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)
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
        self.group = ChurchGroup.objects.create(church=self.church, name="Choir")
        self.other_group = ChurchGroup.objects.create(
            church=self.other_church,
            name="ICT",
        )
        self.admin = User.objects.create_user(
            username="view-admin",
            password="Strong-Test-Password-2026",
            full_name="View Administrator",
            phone_number="255700100020",
            role="ADMIN",
            church=self.church,
        )
        member_user = User.objects.create_user(
            username="view-member",
            password="Strong-Test-Password-2026",
            full_name="View Member",
            phone_number="255700100022",
            role="MEMBER",
            church=self.church,
        )
        image_data = BytesIO()
        Image.new("RGB", (48, 48), color=(75, 59, 143)).save(image_data, "PNG")
        member_user.profile_picture = SimpleUploadedFile(
            "view-member.png",
            image_data.getvalue(),
            content_type="image/png",
        )
        member_user.save(update_fields=["profile_picture"])
        self.member = Member.objects.create(
            user=member_user,
            church=self.church,
            jumuiya=self.jumuiya,
            bahasha_number="VIEW-B-002",
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
            {
                "options": [{"value": self.jumuiya.id, "label": self.jumuiya.name}],
                "groups": [{"value": self.group.id, "label": self.group.name}],
            },
        )
        self.assertEqual(other_response.json(), {"options": [], "groups": []})

    def test_member_picture_endpoint_respects_church_scope(self):
        own_response = self.client.get(
            reverse("web_member_profile_picture", args=[self.member.id])
        )
        other_response = self.client.get(
            reverse("web_member_profile_picture", args=[self.other_member.id])
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response["Content-Type"], "image/png")
        own_response.close()
        self.assertEqual(other_response.status_code, 404)
