from django.db import models
from churches.models import Church


class Jumuiya(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="jumuiya"
    )

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    leader_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Jumuiya"
        verbose_name_plural = "Jumuiya"
        ordering = ["name"]
        unique_together = ("church", "name")

    def __str__(self):
        return f"{self.name} - {self.church.church_name}"