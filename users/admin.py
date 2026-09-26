from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
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
            )
        }),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )