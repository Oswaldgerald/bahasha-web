from django.shortcuts import render

from audit_logs.models import AuditLog
from web.pagination import paginate_queryset
from web.access import audit_access_required, scope_queryset_to_church


@audit_access_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related("user", "church").order_by("-created_at")
    logs = scope_queryset_to_church(logs, request.user)
    logs = paginate_queryset(request, logs)

    return render(request, "audit_logs/list.html", {"logs": logs})
