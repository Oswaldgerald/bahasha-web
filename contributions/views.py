import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from contributions.models import Contribution
from contributions.services import contribution_target_key, save_contribution
from web.forms import ContributionForm


@login_required(login_url="login")
def contribution_list(request):
    contributions = Contribution.objects.select_related(
        "church",
        "member",
        "member__user",
        "financial_year",
        "contribution_week",
        "category",
        "posted_by",
    ).all()

    return render(request, "contributions/list.html", {"contributions": contributions})


@login_required(login_url="login")
def contribution_create(request):
    if request.method == "POST":
        form = ContributionForm(request.POST, request_user=request.user)

        if form.is_valid():
            contribution = form.save(commit=False)

            if not contribution.reference_number:
                contribution.reference_number = (
                    f"MANUAL-{uuid.uuid4().hex[:10].upper()}"
                )

            contribution.source = "MANUAL_ENTRY"
            contribution.posted_by = request.user
            save_contribution(contribution)

            messages.success(request, "Contribution recorded successfully.")
            return redirect("web_contributions")
    else:
        form = ContributionForm(request_user=request.user)

    return render(request, "contributions/create.html", {"form": form})


@login_required(login_url="login")
def contribution_edit(request, contribution_id):
    contribution = get_object_or_404(Contribution, id=contribution_id)
    previous_target_key = contribution_target_key(contribution)

    if request.method == "POST":
        form = ContributionForm(
            request.POST,
            instance=contribution,
            request_user=request.user,
        )

        if form.is_valid():
            updated_contribution = form.save(commit=False)
            save_contribution(updated_contribution, previous_target_key)

            messages.success(request, "Contribution updated successfully.")
            return redirect("web_contributions")
    else:
        form = ContributionForm(instance=contribution, request_user=request.user)

    return render(
        request, "contributions/edit.html", {"form": form, "contribution": contribution}
    )
