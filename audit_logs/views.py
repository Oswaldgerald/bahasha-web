from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from audit_logs.models import AuditLog


@login_required(login_url="login")
def audit_log_list(request):
    logs = AuditLog.objects.select_related("user", "church").all()

    return render(request, "audit_logs/list.html", {"logs": logs})
