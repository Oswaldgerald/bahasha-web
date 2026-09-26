from django.contrib import admin
from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "bahasha_number",
        "user",
        "church",
        "jumuiya",
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
        "is_active",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )