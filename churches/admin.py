from django.contrib import admin
from .models import Church, ChurchGroup


@admin.register(Church)
class ChurchAdmin(admin.ModelAdmin):
    list_display = (
        "church_name",
        "church_code",
        "parish",
        "district",
        "location",
        "is_active",
        "created_at",
    )
    search_fields = (
        "church_name",
        "church_code",
        "parish",
        "district",
    )
    list_filter = (
        "is_active",
        "district",
        "parish",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ChurchGroup)
class ChurchGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "church", "is_active", "created_at")
    list_filter = ("church", "is_active")
    search_fields = ("name", "church__church_name")
    readonly_fields = ("created_at", "updated_at")
