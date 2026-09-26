from django.contrib.auth.models import AbstractUser
from django.db import models
from churches.models import Church


class User(AbstractUser):
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