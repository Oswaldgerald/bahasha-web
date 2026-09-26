from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "church",
        "notification_type",
        "target_role",
        "status",
        "created_by",
        "created_at",
    )
    search_fields = ("title", "message")
    list_filter = ("church", "notification_type", "status", "target_role")