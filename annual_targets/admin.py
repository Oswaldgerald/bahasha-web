from django.contrib import admin
from .models import MemberAnnualTarget


@admin.register(MemberAnnualTarget)
class MemberAnnualTargetAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "church",
        "financial_year",
        "category",
        "target_amount",
        "contributed_amount",
        "remaining_amount",
        "completion_percentage",
        "updated_at",
    )

    search_fields = (
        "member__user__full_name",
        "member__bahasha_number",
        "category__name",
    )

    list_filter = (
        "church",
        "financial_year",
        "category",
    )

    readonly_fields = (
        "remaining_amount",
        "completion_percentage",
        "created_at",
        "updated_at",
    )