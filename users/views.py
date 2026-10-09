from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from audit_logs.services import create_audit_log
from users.forms import ProfileUpdateForm, UserCreateForm, UserForm
from users.models import User
from users.profile_pictures import profile_picture_response
from web.pagination import paginate_queryset
from web.access import church_admin_required, scope_queryset_to_church


def authenticated_home(user):
    if user.role == "MEMBER" and not user.is_superuser:
        return "web_profile"
    return "web_dashboard"


def login_view(request):
    if request.user.is_authenticated:
        return redirect(authenticated_home(request.user))

    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if request.POST.get("remember_me"):
                request.session.set_expiry(None)
            else:
                request.session.set_expiry(0)

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(authenticated_home(user))

        messages.error(request, "Invalid username or password.")

    return render(
        request,
        "users/login.html",
        {
            "next": next_url,
            "username": request.POST.get("username", ""),
            "password_reset_url": reverse("password_reset"),
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@church_admin_required
def user_list(request):
    users = user_queryset_for_user(request.user)
    summary = users.aggregate(
        total=models.Count("id"),
        active=models.Count("id", filter=models.Q(is_active=True)),
        administrators=models.Count("id", filter=models.Q(role="ADMIN")),
        members=models.Count("id", filter=models.Q(role="MEMBER")),
    )

    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    account_status = request.GET.get("account_status", "").strip()
    if query:
        users = users.filter(
            models.Q(full_name__icontains=query)
            | models.Q(username__icontains=query)
            | models.Q(phone_number__icontains=query)
            | models.Q(email__icontains=query)
        )
    if role in dict(User.ROLE_CHOICES):
        users = users.filter(role=role)
    if account_status == "active":
        users = users.filter(is_active=True)
    elif account_status == "inactive":
        users = users.filter(is_active=False)

    users = paginate_queryset(request, users)

    return render(
        request,
        "users/list.html",
        {
            "users": users,
            "summary": summary,
            "role_choices": User.ROLE_CHOICES,
            "filters": {
                "q": query,
                "role": role,
                "account_status": account_status,
            },
        },
    )


def user_queryset_for_user(user):
    users = User.objects.select_related("church").order_by("full_name")
    return scope_queryset_to_church(users, user)


@church_admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()

            messages.success(request, "User created successfully.")

            return redirect("web_users")

    else:
        form = UserCreateForm(request_user=request.user)

    return render(request, "users/create.html", {"form": form})


@church_admin_required
def user_edit(request, user_id):
    user = get_object_or_404(user_queryset_for_user(request.user), id=user_id)

    if request.method == "POST":
        form = UserForm(request.POST, instance=user, request_user=request.user)

        if form.is_valid():
            form.save()

            messages.success(request, "User updated successfully.")

            return redirect("web_users")

    else:
        form = UserForm(instance=user, request_user=request.user)

    return render(request, "users/edit.html", {"form": form, "user_obj": user})


@church_admin_required
@require_POST
def user_reset_password(request, user_id):
    user = get_object_or_404(user_queryset_for_user(request.user), id=user_id)
    if not user.email:
        messages.error(
            request,
            f"Add an email address for {user.full_name} before sending a reset link.",
        )
        return redirect("web_users")

    reset_form = PasswordResetForm({"email": user.email})
    if not reset_form.is_valid():
        messages.error(request, "The password reset request could not be created.")
        return redirect("web_users")

    reset_form.save(
        request=request,
        use_https=request.is_secure(),
        email_template_name="users/password_reset_email.txt",
        subject_template_name="users/password_reset_subject.txt",
    )
    create_audit_log(
        user=request.user,
        church=user.church,
        action="PASSWORD_RESET",
        description=f"Sent a password reset link to user {user.full_name}.",
        entity_type="User",
        entity_id=user.id,
        request=request,
    )

    messages.success(request, f"Password reset link sent to {user.full_name}.")

    return redirect("web_users")


@church_admin_required
@require_POST
def user_activate(request, user_id):
    user = get_object_or_404(user_queryset_for_user(request.user), id=user_id)
    user.is_active = True
    user.save()

    messages.success(request, f"{user.full_name} activated successfully.")

    return redirect("web_users")


@church_admin_required
@require_POST
def user_deactivate(request, user_id):
    user = get_object_or_404(user_queryset_for_user(request.user), id=user_id)

    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("web_users")

    user.is_active = False
    user.save()

    messages.success(request, f"{user.full_name} deactivated successfully.")

    return redirect("web_users")


@login_required(login_url="login")
def profile_view(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("web_profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "profile/detail.html", {"form": form})


@login_required(login_url="login")
def profile_picture_view(request):
    return profile_picture_response(request.user)


@login_required(login_url="login")
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully.")
            return redirect("web_profile")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "profile/change_password.html", {"form": form})
