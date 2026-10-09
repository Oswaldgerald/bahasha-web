from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from annual_targets.models import MemberAnnualTarget
from web.forms import MemberAnnualTargetForm


def annual_target_list(request):
    targets = MemberAnnualTarget.objects.select_related(
        "member",
        "member__user",
        "church",
        "financial_year",
        "category",
    ).all()

    return render(request, "annual_targets/list.html", {"targets": targets})


@login_required(login_url="login")
def annual_target_create(request):
    if request.method == "POST":
        form = MemberAnnualTargetForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Annual target created successfully.")
            return redirect("web_annual_targets")
    else:
        form = MemberAnnualTargetForm(request_user=request.user)

    return render(request, "annual_targets/create.html", {"form": form})


@login_required(login_url="login")
def annual_target_edit(request, target_id):
    target = get_object_or_404(MemberAnnualTarget, id=target_id)

    if request.method == "POST":
        form = MemberAnnualTargetForm(
            request.POST,
            instance=target,
            request_user=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Annual target updated successfully.")
            return redirect("web_annual_targets")
    else:
        form = MemberAnnualTargetForm(instance=target, request_user=request.user)

    return render(request, "annual_targets/edit.html", {"form": form, "target": target})
