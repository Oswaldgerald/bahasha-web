from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from audit_logs.models import AuditLog
from web.pagination import paginate_queryset


@login_required(login_url="login")
def audit_log_list(request):
    logs = AuditLog.objects.select_related("user", "church").order_by("-created_at")
    logs = paginate_queryset(request, logs)

    return render(request, "audit_logs/list.html", {"logs": logs})
