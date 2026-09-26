from django.db import models
from users.models import User
from churches.models import Church
from jumuiya.models import Jumuiya


class Member(models.Model):
    APPROVAL_STATUS = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="member_profile"
    )

    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="members"
    )

    jumuiya = models.ForeignKey(
        Jumuiya,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members"
    )

    bahasha_number = models.CharField(
        max_length=100,
        unique=True
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    demographics = models.TextField(
        blank=True,
        null=True
    )

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="PENDING"
    )

    approved_at = models.DateTimeField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Member"
        verbose_name_plural = "Members"
        ordering = ["user__full_name"]

    def __str__(self):
        return f"{self.user.full_name} ({self.bahasha_number})"