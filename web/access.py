from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


CHURCH_ADMIN_ROLES = {"ADMIN", "MAIN_PASTOR"}
MEMBER_MANAGEMENT_ROLES = CHURCH_ADMIN_ROLES | {
    "ASSISTANT_PASTOR",
    "CONGREGATION_ELDER",
}
FINANCE_MANAGEMENT_ROLES = CHURCH_ADMIN_ROLES | {"FINANCE_OFFICER"}
REPORT_ACCESS_ROLES = MEMBER_MANAGEMENT_ROLES | {"FINANCE_OFFICER", "AUDITOR"}
NOTIFICATION_MANAGEMENT_ROLES = CHURCH_ADMIN_ROLES | {"ASSISTANT_PASTOR"}
AUDIT_ACCESS_ROLES = CHURCH_ADMIN_ROLES | {"AUDITOR"}
STAFF_DASHBOARD_ROLES = REPORT_ACCESS_ROLES


def role_required(*roles):
    allowed_roles = set(roles)

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url="login")
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to access this page.")

        return wrapped

    return decorator


def superuser_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="login")
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Only a system administrator can access this page.")

    return wrapped


church_admin_required = role_required(*CHURCH_ADMIN_ROLES)
member_management_required = role_required(*MEMBER_MANAGEMENT_ROLES)
finance_management_required = role_required(*FINANCE_MANAGEMENT_ROLES)
report_access_required = role_required(*REPORT_ACCESS_ROLES)
notification_management_required = role_required(*NOTIFICATION_MANAGEMENT_ROLES)
audit_access_required = role_required(*AUDIT_ACCESS_ROLES)
staff_dashboard_required = role_required(*STAFF_DASHBOARD_ROLES)


def scope_queryset_to_church(queryset, user, church_field="church"):
    if user.is_superuser:
        return queryset
    if not user.church_id:
        return queryset.none()
    lookup = "pk" if church_field == "pk" else f"{church_field}_id"
    return queryset.filter(**{lookup: user.church_id})
