import uuid

from django.db import models
from django.conf import settings
from churches.models import Church


class Notification(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    TYPE_CHOICES = [
        ("CONTRIBUTION_UPDATE", "Contribution Update"),
        ("TARGET_UPDATE", "Annual Target Update"),
        ("REMINDER", "Reminder Alert"),
        ("CHURCH_ANNOUNCEMENT", "Church Announcement"),
        ("SYSTEM_MESSAGE", "System Message"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
    ]

    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES
    )

    target_role = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Leave blank to send to all users in the church"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications"
    )

    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class NotificationReceipt(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_receipts",
    )
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"],
                name="unique_notification_receipt_per_user",
            )
        ]


class MobileDevice(models.Model):
    PLATFORM_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_devices",
    )
    installation_id = models.UUIDField()
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    push_token = models.CharField(max_length=512)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "installation_id"],
                name="unique_mobile_installation_per_user",
            )
        ]
