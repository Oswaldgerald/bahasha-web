from django.db import models
from django.conf import settings
from churches.models import Church
from members.models import Member
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from categories.models import ContributionCategory


class Contribution(models.Model):
    SOURCE_CHOICES = [
        ("EXCEL_UPLOAD", "Excel Upload"),
        ("MANUAL_ENTRY", "Manual Entry"),
        ("ONLINE_PAYMENT", "Online Payment"),
        ("CORRECTION", "Correction"),
    ]

    STATUS_CHOICES = [
        ("POSTED", "Posted"),
        ("PENDING", "Pending"),
        ("REVERSED", "Reversed"),
    ]

    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="contributions"
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="contributions"
    )

    bahasha_number = models.CharField(max_length=100)

    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name="contributions"
    )

    contribution_week = models.ForeignKey(
        ContributionWeek,
        on_delete=models.CASCADE,
        related_name="contributions"
    )

    category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.CASCADE,
        related_name="contributions"
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    contribution_date = models.DateField()

    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="POSTED"
    )

    reference_number = models.CharField(
        max_length=100,
        unique=True
    )

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_contributions"
    )

    posted_at = models.DateTimeField(auto_now_add=True)

    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contribution"
        verbose_name_plural = "Contributions"
        ordering = ["-contribution_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.member.user.full_name} - "
            f"{self.category.name} - "
            f"{self.amount}"
        )