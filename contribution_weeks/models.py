from django.db import models
from churches.models import Church
from financial_years.models import FinancialYear


class ContributionWeek(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="contribution_weeks"
    )

    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name="weeks"
    )

    week_number = models.PositiveIntegerField()
    sunday_date = models.DateField()
    is_active = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contribution Week"
        verbose_name_plural = "Contribution Weeks"
        ordering = ["-sunday_date"]
        unique_together = ("church", "financial_year", "week_number")

    def __str__(self):
        return f"{self.church.church_name} - Week {self.week_number} ({self.sunday_date})"
    def save(self, *args, **kwargs):
        if self.is_active:
            ContributionWeek.objects.filter(
                church=self.church
            ).exclude(
                id=self.id
            ).update(is_active=False)

        super().save(*args, **kwargs)
