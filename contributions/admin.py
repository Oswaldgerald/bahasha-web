from django.contrib import admin
from .models import Contribution


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "member",
        "bahasha_number",
        "church",
        "financial_year",
        "contribution_week",
        "category",
        "amount",
        "source",
        "status",
        "contribution_date",
        "posted_by",
    )

    search_fields = (
        "reference_number",
        "member__user__full_name",
        "member__bahasha_number",
        "bahasha_number",
    )

    list_filter = (
        "church",
        "financial_year",
        "category",
        "source",
        "status",
        "contribution_date",
    )

    readonly_fields = (
        "posted_at",
        "created_at",
    )