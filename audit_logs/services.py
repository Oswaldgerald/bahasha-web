from audit_logs.models import AuditLog


def create_audit_log(
    *,
    user=None,
    church=None,
    action="OTHER",
    description="",
    entity_type=None,
    entity_id=None,
    request=None
):
    ip_address = None

    if request:
        ip_address = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=user,
        church=church,
        action=action,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
    )