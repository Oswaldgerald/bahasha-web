from django.db import models
from members.models import Member
from churches.models import Church
from financial_years.models import FinancialYear
from categories.models import ContributionCategory


class MemberAnnualTarget(models.Model):
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="annual_targets"
    )

    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="annual_targets"
    )

    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name="annual_targets"
    )

    category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.CASCADE,
        related_name="annual_targets"
    )

    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    contributed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    remaining_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    completion_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Member Annual Target"
        verbose_name_plural = "Member Annual Targets"
        unique_together = (
            "member",
            "financial_year",
            "category",
        )
        ordering = ["member__user__full_name", "category__name"]

    def save(self, *args, **kwargs):
        self.remaining_amount = self.target_amount - self.contributed_amount

        if self.target_amount > 0:
            self.completion_percentage = (
                self.contributed_amount / self.target_amount
            ) * 100
        else:
            self.completion_percentage = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.member.user.full_name} - "
            f"{self.category.name} - "
            f"{self.financial_year.year}"
        )