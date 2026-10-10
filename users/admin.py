from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from config.admin_mixins import RowDeleteActionMixin

from .models import User


@admin.register(User)
class CustomUserAdmin(RowDeleteActionMixin, UserAdmin):
    model = User

    list_display = (
        "username",
        "full_name",
        "phone_number",
        "role",
        "church",
        "is_active",
        "is_staff",
        "created_at",
    )

    search_fields = (
        "username",
        "full_name",
        "phone_number",
        "email",
        "church__church_name",
    )

    list_filter = (
        "role",
        "church",
        "is_active",
        "is_staff",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("Bahasha User Details", {
            "fields": (
                "full_name",
                "phone_number",
                "role",
                "church",
                "profile_picture",
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Bahasha User Details", {
            "fields": (
                "full_name",
                "phone_number",
                "role",
                "church",
                "profile_picture",
            )
        }),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.pk == request.user.pk:
            return False
        return super().has_delete_permission(request, obj)
