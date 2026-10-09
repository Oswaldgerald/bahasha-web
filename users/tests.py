from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from churches.models import Church
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


class ProfilePictureTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.user = User.objects.create_user(
            username="profile-user",
            password="strong-test-password",
            full_name="Profile User",
            phone_number="255700000099",
            role="ADMIN",
        )
        self.client.force_login(self.user)

    @staticmethod
    def profile_picture():
        image_data = BytesIO()
        Image.new("RGB", (64, 64), color=(45, 27, 105)).save(image_data, "PNG")
        return SimpleUploadedFile(
            "avatar.png",
            image_data.getvalue(),
            content_type="image/png",
        )

    def test_user_can_upload_and_view_private_profile_picture(self):
        response = self.client.post(
            reverse("web_profile"),
            {
                "full_name": self.user.full_name,
                "phone_number": self.user.phone_number,
                "profile_picture": self.profile_picture(),
            },
        )

        self.assertRedirects(response, reverse("web_profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "+255700000099")
        self.assertTrue(self.user.profile_picture.name.startswith("profile_pictures/user_"))

        picture_response = self.client.get(reverse("web_profile_picture"))
        self.assertEqual(picture_response.status_code, 200)
        self.assertEqual(picture_response["Content-Type"], "image/png")
        self.assertEqual(picture_response["Cache-Control"], "private, no-store")
        picture_response.close()

    def test_profile_picture_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse("web_profile_picture"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('web_profile_picture')}",
        )

    def test_user_can_remove_profile_picture_and_stored_file(self):
        upload_response = self.client.post(
            reverse("web_profile"),
            {
                "full_name": self.user.full_name,
                "phone_number": self.user.phone_number,
                "profile_picture": self.profile_picture(),
            },
        )
        self.assertRedirects(upload_response, reverse("web_profile"))
        self.user.refresh_from_db()
        stored_name = self.user.profile_picture.name
        storage = self.user.profile_picture.storage
        self.assertTrue(storage.exists(stored_name))

        response = self.client.post(
            reverse("web_profile"),
            {
                "full_name": self.user.full_name,
                "phone_number": self.user.phone_number,
                "remove_picture": "on",
            },
        )

        self.assertRedirects(response, reverse("web_profile"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_picture)
        self.assertFalse(storage.exists(stored_name))
        self.assertEqual(self.client.get(reverse("web_profile_picture")).status_code, 404)


class UserManagementTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="USR-001",
            church_name="User Test Church",
        )
        self.other_church = Church.objects.create(
            church_code="USR-002",
            church_name="Other User Church",
        )
        self.admin = User.objects.create_user(
            username="user-admin",
            password="strong-test-password",
            full_name="User Administrator",
            phone_number="255700000110",
            role="ADMIN",
            church=self.church,
        )
        self.member = User.objects.create_user(
            username="managed-member",
            password="strong-test-password",
            full_name="Managed Member",
            phone_number="255700000111",
            role="MEMBER",
            church=self.church,
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            password="strong-test-password",
            full_name="Other User",
            phone_number="255700000112",
            role="MEMBER",
            church=self.other_church,
        )
        self.client.force_login(self.admin)

    def test_user_list_has_status_column_and_is_scoped_to_church(self):
        response = self.client.get(reverse("web_users"))

        self.assertContains(response, "Status")
        self.assertContains(response, self.member.full_name)
        self.assertNotContains(response, self.other_user.full_name)

    def test_user_filters_by_role_and_account_state(self):
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])

        response = self.client.get(
            reverse("web_users"),
            {"role": "MEMBER", "account_status": "inactive"},
        )

        self.assertQuerySetEqual(response.context["users"], [self.member])

    def test_password_reset_requires_post(self):
        url = reverse("web_user_reset_password", args=[self.member.id])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(url), reverse("web_users"))

    def test_user_creation_sets_the_submitted_password(self):
        response = self.client.post(
            reverse("web_user_create"),
            {
                "full_name": "New Finance User",
                "username": "new-finance-user",
                "phone_country_code": "255",
                "phone_number": "700000113",
                "church": self.church.id,
                "role": "FINANCE_OFFICER",
                "is_active": "on",
                "password1": "N4!vQ8@zL2#p",
                "password2": "N4!vQ8@zL2#p",
            },
        )

        self.assertRedirects(response, reverse("web_users"))
        created_user = User.objects.get(username="new-finance-user")
        self.assertTrue(created_user.check_password("N4!vQ8@zL2#p"))
        self.assertFalse(created_user.check_password("Password123"))

    def test_user_creation_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("web_user_create"),
            {
                "full_name": "Mismatched Password",
                "username": "mismatched-password",
                "phone_country_code": "255",
                "phone_number": "700000114",
                "church": self.church.id,
                "role": "MEMBER",
                "is_active": "on",
                "password1": "Secure-Password-2026!",
                "password2": "Different-Password-2026!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two passwords do not match.")
        self.assertFalse(User.objects.filter(username="mismatched-password").exists())

    def test_user_edit_keeps_the_existing_password(self):
        password_hash = self.member.password

        get_response = self.client.get(
            reverse("web_user_edit", args=[self.member.id])
        )
        self.assertNotContains(get_response, 'id="id_password1"')
        self.assertNotContains(get_response, 'id="id_password2"')

        response = self.client.post(
            reverse("web_user_edit", args=[self.member.id]),
            {
                "full_name": "Updated Managed Member",
                "username": self.member.username,
                "phone_country_code": "255",
                "phone_number": "700000111",
                "church": self.church.id,
                "role": self.member.role,
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("web_users"))
        self.member.refresh_from_db()
        self.assertEqual(self.member.password, password_hash)
