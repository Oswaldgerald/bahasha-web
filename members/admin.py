from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import Member


@admin.register(Member)
class MemberAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "bahasha_number",
        "user",
        "church",
        "jumuiya",
        "marital_status",
        "approval_status",
        "is_active",
        "created_at",
    )

    search_fields = (
        "bahasha_number",
        "user__full_name",
        "user__phone_number",
    )

    list_filter = (
        "approval_status",
        "church",
        "jumuiya",
        "marital_status",
        "church_groups",
        "is_active",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
