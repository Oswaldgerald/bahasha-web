from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from churches.models import Church
from jumuiya.models import Jumuiya


class Member(models.Model):
    APPROVAL_STATUS = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
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
        choices=GENDER_CHOICES,
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

    def clean(self):
        super().clean()
        errors = {}

        if self.user_id and self.church_id and self.user.church_id != self.church_id:
            errors["church"] = "Member and user account must belong to the same church."

        if self.jumuiya_id and self.church_id and self.jumuiya.church_id != self.church_id:
            errors["jumuiya"] = "Jumuiya must belong to the selected church."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user.full_name} ({self.bahasha_number})"
