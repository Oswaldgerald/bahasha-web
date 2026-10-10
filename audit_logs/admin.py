from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "action",
        "user",
        "church",
        "entity_type",
        "entity_id",
        "created_at",
    )
    search_fields = (
        "action",
        "description",
        "entity_type",
        "entity_id",
        "user__full_name",
    )
    list_filter = (
        "action",
        "church",
        "created_at",
    )
    readonly_fields = (
        "created_at",
    )
