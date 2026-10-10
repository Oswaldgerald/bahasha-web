from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import Jumuiya


@admin.register(Jumuiya)
class JumuiyaAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "church",
        "leader_name",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "leader_name",
        "church__church_name",
    )

    list_filter = (
        "church",
        "is_active",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
