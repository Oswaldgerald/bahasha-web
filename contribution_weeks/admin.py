from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import ContributionWeek


@admin.register(ContributionWeek)
class ContributionWeekAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "church",
        "financial_year",
        "week_number",
        "sunday_date",
        "is_active",
        "is_closed",
    )
    search_fields = (
        "church__church_name",
        "week_number",
    )
    list_filter = (
        "church",
        "financial_year",
        "is_active",
        "is_closed",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
