from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from audit_logs.services import create_audit_log
from users.forms import ProfileUpdateForm, UserForm
from users.models import User
from users.profile_pictures import profile_picture_response


def login_view(request):
    if request.user.is_authenticated:
        return redirect("web_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("web_dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "users/login.html")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def user_list(request):
    users = User.objects.select_related("church").order_by("full_name")

    return render(request, "users/list.html", {"users": users})


@login_required(login_url="login")
def user_create(request):
    if request.method == "POST":
        form = UserForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # Default password
            user.set_password("Password123")

            user.save()

            messages.success(request, "User created successfully.")

            return redirect("web_users")

    else:
        form = UserForm()

    return render(request, "users/create.html", {"form": form})


@login_required(login_url="login")
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UserForm(request.POST, instance=user)

        if form.is_valid():
            form.save()

            messages.success(request, "User updated successfully.")

            return redirect("web_users")

    else:
        form = UserForm(instance=user)

    return render(request, "users/edit.html", {"form": form, "user_obj": user})


@login_required(login_url="login")
def user_reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id)

    user.set_password("Password123")
    user.save()
    create_audit_log(
        user=request.user,
        church=user.church,
        action="PASSWORD_RESET",
        description=f"Reset password for user {user.full_name}.",
        entity_type="User",
        entity_id=user.id,
        request=request,
    )

    messages.success(request, f"Password reset for {user.full_name}")

    return redirect("web_users")


@login_required(login_url="login")
@require_POST
def user_activate(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    messages.success(request, f"{user.full_name} activated successfully.")

    return redirect("web_users")


@login_required(login_url="login")
@require_POST
def user_deactivate(request, user_id):
    user = get_object_or_404(User, id=user_id)

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
