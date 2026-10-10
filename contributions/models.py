import uuid

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from churches.models import Church
from members.models import Member
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from categories.models import ContributionCategory


class Contribution(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="contribution_amount_positive",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Contribution amount must be greater than zero."

        if self.member_id and self.church_id:
            if self.member.church_id != self.church_id:
                errors["member"] = "Member must belong to the selected church."
            elif self._state.adding and (
                not self.member.is_active or self.member.approval_status != "APPROVED"
            ):
                errors["member"] = "Member must be active and approved."

        if self.financial_year_id and self.church_id:
            if self.financial_year.church_id != self.church_id:
                errors["financial_year"] = "Financial year must belong to the selected church."

        if self.contribution_week_id:
            if self.church_id and self.contribution_week.church_id != self.church_id:
                errors["contribution_week"] = "Contribution week must belong to the selected church."
            elif (
                self.financial_year_id
                and self.contribution_week.financial_year_id != self.financial_year_id
            ):
                errors["contribution_week"] = "Contribution week must belong to the selected financial year."

        if self.category_id and self._state.adding and not self.category.is_active:
            errors["category"] = "Contribution category must be active."
        if (
            self.category_id
            and self.church_id
            and self.category.church_id != self.church_id
        ):
            errors["category"] = "Contribution category must belong to the selected church."

        if self.contribution_date and self.financial_year_id:
            if not (
                self.financial_year.start_date
                <= self.contribution_date
                <= self.financial_year.end_date
            ):
                errors["contribution_date"] = "Contribution date must fall within the financial year."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.member.user.full_name} - "
            f"{self.category.name} - "
            f"{self.amount}"
        )
