import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.text import slugify

from churches.models import Church


class ContributionCategory(models.Model):
    FREQUENCY_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("ANNUAL", "Annual"),
        ("SEASONAL", "Seasonal"),
    ]

    ICON_CHOICES = [
        ("hand-heart", "Hand and heart"),
        ("landmark", "Church building"),
        ("scale", "Scale"),
        ("users-round", "Community"),
        ("tractor", "Harvest"),
        ("gift", "Gift"),
        ("heart-handshake", "Partnership"),
        ("badge-dollar-sign", "Fund"),
        ("building-2", "Building project"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="contribution_categories",
    )

    name = models.CharField(max_length=100)
    name_sw = models.CharField(max_length=100, blank=True)
    key = models.SlugField(max_length=80)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default="WEEKLY"
    )

    display_order = models.PositiveIntegerField(default=1)
    is_annual = models.BooleanField(default=False)
    icon_key = models.CharField(
        max_length=40,
        choices=ICON_CHOICES,
        default="hand-heart",
    )
    theme_color = models.CharField(
        max_length=7,
        default="#2D1B69",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Enter a six-digit hex color such as #2D1B69.",
            )
        ],
    )
    suggested_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    minimum_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    maximum_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    is_mobile_visible = models.BooleanField(default=True)
    allows_member_payment = models.BooleanField(default=True)
    allows_catch_up = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contribution Category"
        verbose_name_plural = "Contribution Categories"
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["church", "key"],
                name="unique_category_key_per_church",
            ),
            models.UniqueConstraint(
                fields=["church", "name"],
                name="unique_category_name_per_church",
            ),
            models.UniqueConstraint(
                fields=["church", "code"],
                name="unique_category_code_per_church",
            ),
        ]
        indexes = [
            models.Index(
                fields=["church", "is_active", "is_mobile_visible"],
                name="category_mobile_lookup",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.minimum_amount is not None
            and self.maximum_amount is not None
            and self.minimum_amount > self.maximum_amount
        ):
            errors["maximum_amount"] = "Maximum amount must be at least the minimum amount."
        if self.suggested_amount is not None:
            if (
                self.minimum_amount is not None
                and self.suggested_amount < self.minimum_amount
            ):
                errors["suggested_amount"] = "Suggested amount cannot be below the minimum amount."
            if (
                self.maximum_amount is not None
                and self.suggested_amount > self.maximum_amount
            ):
                errors["suggested_amount"] = "Suggested amount cannot exceed the maximum amount."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.code or self.name)
        self.code = self.code.upper() if self.code else None
        self.is_annual = self.frequency == "ANNUAL"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.church.church_name}"
