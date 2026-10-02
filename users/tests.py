from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
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
