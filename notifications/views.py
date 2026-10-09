from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from audit_logs.services import create_audit_log
from notifications.models import Notification
from web.forms import NotificationForm
from web.pagination import paginate_queryset
from web.access import notification_management_required, scope_queryset_to_church


@notification_management_required
def notification_list(request):
    notifications = Notification.objects.select_related(
        "church",
        "created_by",
    ).order_by("-created_at")
    notifications = scope_queryset_to_church(notifications, request.user)
    notifications = paginate_queryset(request, notifications)

    return render(request, "notifications/list.html", {"notifications": notifications})


@notification_management_required
def notification_create(request):
    if request.method == "POST":
        form = NotificationForm(request.POST, request_user=request.user)

        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.status = "SENT"
            notification.sent_at = timezone.now()
            notification.save()

            create_audit_log(
                user=request.user,
                church=notification.church,
                action="OTHER",
                description=f"Sent notification: {notification.title}",
                entity_type="Notification",
                entity_id=notification.id,
                request=request,
            )

            messages.success(request, "Notification sent successfully.")
            return redirect("web_notifications")
    else:
        form = NotificationForm(request_user=request.user)

    return render(request, "notifications/create.html", {"form": form})
