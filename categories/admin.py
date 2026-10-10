from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import ContributionCategory


@admin.register(ContributionCategory)
class ContributionCategoryAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "church",
        "frequency",
        "is_mobile_visible",
        "allows_member_payment",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "name_sw", "key", "code", "church__church_name")
    list_filter = (
        "church",
        "frequency",
        "is_mobile_visible",
        "allows_member_payment",
        "is_active",
    )
    readonly_fields = ("public_id", "created_at", "updated_at")
