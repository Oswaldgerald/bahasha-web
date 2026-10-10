from django.contrib.auth.models import AbstractUser
from django.db import models
from pathlib import Path
import uuid

from churches.models import Church


def profile_picture_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"profile_pictures/user_{instance.pk}/{uuid.uuid4().hex}{extension}"


class User(AbstractUser):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    ROLE_CHOICES = [
            ("MAIN_PASTOR", "Main Pastor"),
            ("ASSISTANT_PASTOR", "Assistant Pastor"),
            ("CONGREGATION_ELDER", "Congregation Elder"),
            ("ADMIN", "Administrator"),
            ("FINANCE_OFFICER", "Finance Officer"),
            ("AUDITOR", "Auditor"),
            ("MEMBER", "Member"),
    ]

    church = models.ForeignKey(
        Church,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    profile_picture = models.ImageField(
        upload_to=profile_picture_path,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["full_name", "phone_number", "role"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} - {self.role}"


class ApiTokenSession(models.Model):
    PLATFORM_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    family_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_token_sessions",
    )
    access_token_hash = models.CharField(max_length=64, unique=True)
    refresh_token_hash = models.CharField(max_length=64, unique=True)
    installation_id = models.UUIDField()
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    app_version = models.CharField(max_length=40, blank=True)
    device_name = models.CharField(max_length=120, blank=True)
    access_expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["refresh_expires_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.public_id}"
