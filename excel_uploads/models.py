from django.db import models
from django.conf import settings

from churches.models import Church
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from categories.models import ContributionCategory
from members.models import Member


class ExcelUpload(models.Model):
    STATUS_CHOICES = [
        ("PENDING_VALIDATION", "Pending Validation"),
        ("VALIDATED", "Validated"),
        ("APPROVED", "Approved"),
        ("POSTED", "Posted"),
        ("FAILED", "Failed"),
    ]

    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="excel_uploads"
    )

    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name="excel_uploads"
    )

    contribution_week = models.ForeignKey(
        ContributionWeek,
        on_delete=models.CASCADE,
        related_name="excel_uploads"
    )

    selected_category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.CASCADE,
        related_name="excel_uploads"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="excel_uploads"
    )

    file = models.FileField(upload_to="excel_uploads/")
    file_name = models.CharField(max_length=255)
    upload_reference = models.CharField(max_length=100, unique=True)

    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING_VALIDATION"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_excel_uploads"
    )

    approved_at = models.DateTimeField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Excel Upload"
        verbose_name_plural = "Excel Uploads"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.upload_reference} - {self.church.church_name}"


class ExcelUploadRow(models.Model):
    VALIDATION_STATUS = [
        ("VALID", "Valid"),
        ("INVALID", "Invalid"),
    ]

    upload = models.ForeignKey(
        ExcelUpload,
        on_delete=models.CASCADE,
        related_name="rows"
    )

    row_number = models.PositiveIntegerField()
    bahasha_number = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    resolved_member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="excel_upload_rows"
    )

    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS,
        default="INVALID"
    )

    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Excel Upload Row"
        verbose_name_plural = "Excel Upload Rows"
        ordering = ["row_number"]

    def __str__(self):
        return f"Row {self.row_number} - {self.bahasha_number}"