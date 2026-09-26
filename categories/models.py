from django.db import models


from django.db import models


class ContributionCategory(models.Model):
    FREQUENCY_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("ANNUAL", "Annual"),
        ("SEASONAL", "Seasonal"),
    ]

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default="WEEKLY"
    )

    display_order = models.PositiveIntegerField(default=1)
    is_annual = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contribution Category"
        verbose_name_plural = "Contribution Categories"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name