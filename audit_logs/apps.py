from django.apps import AppConfig


class AuditLogsConfig(AppConfig):
    """Register immutable audit events with Django."""

    name = "audit_logs"
    verbose_name = "Audit Logs"
