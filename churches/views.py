from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from churches.models import Church, ChurchGroup
from categories.services import create_default_categories
from web.forms import ChurchForm
from web.pagination import paginate_queryset

from .forms import ChurchGroupForm


@login_required(login_url="login")
def church_list(request):
    churches = Church.objects.all().order_by("church_name")
    churches = paginate_queryset(request, churches)

    return render(request, "churches/list.html", {"churches": churches})


@login_required(login_url="login")
def church_create(request):
    if request.method == "POST":
        form = ChurchForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                church = form.save()
                create_default_categories(church)
            messages.success(
                request,
                "Church created with the default contribution categories.",
            )
            return redirect("web_churches")
    else:
        form = ChurchForm()

    return render(request, "churches/create.html", {"form": form})


@login_required(login_url="login")
def church_edit(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    if request.method == "POST":
        form = ChurchForm(request.POST, instance=church)

        if form.is_valid():
            form.save()
            messages.success(request, "Church updated successfully.")
            return redirect("web_churches")
    else:
        form = ChurchForm(instance=church)

    return render(request, "churches/edit.html", {"form": form, "church": church})


def church_group_queryset_for_user(user):
    groups = ChurchGroup.objects.select_related("church").annotate(
        member_count=Count("members")
    )
    if user.church_id and not user.is_superuser:
        groups = groups.filter(church_id=user.church_id)
    return groups


@login_required(login_url="login")
def church_group_list(request):
    groups = church_group_queryset_for_user(request.user).order_by(
        "church__church_name", "name"
    )
    return render(
        request,
        "churches/group_list.html",
        {"church_groups": paginate_queryset(request, groups)},
    )


@login_required(login_url="login")
def church_group_create(request):
    form = ChurchGroupForm(request.POST or None, request_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Church group created successfully.")
        return redirect("web_church_groups")

    return render(
        request,
        "churches/group_form.html",
        {"form": form, "submit_label": "Save Group"},
    )


@login_required(login_url="login")
def church_group_edit(request, group_id):
    church_group = get_object_or_404(
        church_group_queryset_for_user(request.user),
        id=group_id,
    )
    form = ChurchGroupForm(
        request.POST or None,
        instance=church_group,
        request_user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Church group updated successfully.")
        return redirect("web_church_groups")

    return render(
        request,
        "churches/group_form.html",
        {"form": form, "submit_label": "Update Group"},
    )
