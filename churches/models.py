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