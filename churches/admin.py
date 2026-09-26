from django.contrib import admin
from .models import Church


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