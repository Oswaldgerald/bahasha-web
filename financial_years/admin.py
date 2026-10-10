from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import FinancialYear


@admin.register(FinancialYear)
class FinancialYearAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "church",
        "year",
        "start_date",
        "end_date",
        "is_active",
        "created_at",
    )
    search_fields = (
        "church__church_name",
        "year",
    )
    list_filter = (
        "church",
        "is_active",
        "year",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
