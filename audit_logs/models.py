from django.db import models
from django.conf import settings
from churches.models import Church


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("USER_CREATED", "User Created"),
        ("USER_UPDATED", "User Updated"),
        ("PASSWORD_RESET", "Password Reset"),
        ("MEMBER_CREATED", "Member Created"),
        ("MEMBER_APPROVED", "Member Approved"),
        ("MEMBER_REJECTED", "Member Rejected"),
        ("EXCEL_UPLOADED", "Excel Uploaded"),
        ("EXCEL_APPROVED", "Excel Approved"),
        ("CONTRIBUTION_CREATED", "Contribution Created"),
        ("TARGET_UPDATED", "Target Updated"),
        ("CHURCH_UPDATED", "Church Updated"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("PROFILE_UPDATED", "Profile Updated"),
        ("DEVICE_REGISTERED", "Device Registered"),
        ("OTHER", "Other"),
    ]

    church = models.ForeignKey(
        Church,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    entity_type = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.created_at}"
