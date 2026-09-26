from django.db import models
from django.conf import settings
from churches.models import Church


class Notification(models.Model):
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