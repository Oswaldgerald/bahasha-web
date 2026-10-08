import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
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

    if request.user.church_id and not request.user.is_superuser:
        contributions = contributions.filter(church_id=request.user.church_id)

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    source_filter = request.GET.get("source", "").strip().upper()

    if query:
        contributions = contributions.filter(
            Q(member__user__full_name__icontains=query)
            | Q(bahasha_number__icontains=query)
            | Q(reference_number__icontains=query)
            | Q(category__name__icontains=query)
        )
    if status_filter in dict(Contribution.STATUS_CHOICES):
        contributions = contributions.filter(status=status_filter)
    else:
        status_filter = ""
    if source_filter in dict(Contribution.SOURCE_CHOICES):
        contributions = contributions.filter(source=source_filter)
    else:
        source_filter = ""

    summary = contributions.aggregate(
        total=Count("id"),
        amount=Sum("amount", default=0),
    )
    contribution_page = Paginator(contributions, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "contributions/list.html",
        {
            "contributions": contribution_page,
            "summary": summary,
            "filters": {
                "q": query,
                "status": status_filter,
                "source": source_filter,
            },
            "status_choices": Contribution.STATUS_CHOICES,
            "source_choices": Contribution.SOURCE_CHOICES,
        },
    )


@login_required(login_url="login")
def contribution_create(request):
    if request.method == "POST":
        form = ContributionForm(request.POST)

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
        form = ContributionForm()

    return render(request, "contributions/create.html", {"form": form})


@login_required(login_url="login")
def contribution_edit(request, contribution_id):
    contribution = get_object_or_404(Contribution, id=contribution_id)
    previous_target_key = contribution_target_key(contribution)

    if request.method == "POST":
        form = ContributionForm(request.POST, instance=contribution)

        if form.is_valid():
            updated_contribution = form.save(commit=False)
            save_contribution(updated_contribution, previous_target_key)

            messages.success(request, "Contribution updated successfully.")
            return redirect("web_contributions")
    else:
        form = ContributionForm(instance=contribution)

    return render(
        request, "contributions/edit.html", {"form": form, "contribution": contribution}
    )
