from django.contrib import admin
from .models import ContributionCategory


@admin.register(ContributionCategory)
class ContributionCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "frequency",
        "is_active",
        "created_at",
    )
    search_fields = ("name",)
    list_filter = ("frequency", "is_active")
    readonly_fields = ("created_at", "updated_at")