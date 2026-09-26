from django.db import models
from churches.models import Church


class FinancialYear(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="financial_years"
    )

    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Financial Year"
        verbose_name_plural = "Financial Years"
        ordering = ["-year"]
        unique_together = ("church", "year")

    def __str__(self):
        return f"{self.church.church_name} - {self.year}"