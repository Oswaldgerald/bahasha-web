from django.db import models


class Church(models.Model):
    church_code = models.CharField(max_length=50, unique=True)
    church_name = models.CharField(max_length=255)
    parish = models.CharField(max_length=255, blank=True, null=True)
    district = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Church"
        verbose_name_plural = "Churches"
        ordering = ["church_name"]

    def __str__(self):
        return f"{self.church_name} ({self.church_code})"


class ChurchGroup(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="church_groups",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["church", "name"],
                name="unique_church_group_name",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.church.church_name}"
