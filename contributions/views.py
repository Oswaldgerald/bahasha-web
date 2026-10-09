import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse

from contributions.models import Contribution
from contributions.services import contribution_target_key, save_contribution
from excel_uploads.models import ExcelUpload
from excel_uploads.services import create_excel_upload
from web.forms import ContributionForm, ExcelUploadForm
from web.pagination import paginate_queryset

from .forms import ContributionFilterForm


WORKSPACE_TABS = {"records", "manual", "upload", "uploads"}


def _scope_to_user_church(queryset, user):
    if user.is_superuser or not user.church_id:
        return queryset
    return queryset.filter(church_id=user.church_id)


def _save_manual_contribution(form, user):
    contribution = form.save(commit=False)
    if not contribution.reference_number:
        contribution.reference_number = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"
    contribution.source = "MANUAL_ENTRY"
    contribution.posted_by = user
    save_contribution(contribution)


@login_required(login_url="login")
def contribution_list(request):
    requested_tab = request.POST.get("entry_mode") or request.GET.get("tab", "records")
    active_tab = requested_tab if requested_tab in WORKSPACE_TABS else "records"

    contribution_form = ContributionForm(request_user=request.user)
    upload_form = ExcelUploadForm(request_user=request.user)

    if request.method == "POST" and active_tab == "manual":
        contribution_form = ContributionForm(
            request.POST,
            request_user=request.user,
        )
        if contribution_form.is_valid():
            _save_manual_contribution(contribution_form, request.user)
            messages.success(request, "Contribution recorded successfully.")
            return redirect(f"{reverse('web_contributions')}?tab=records")

    if request.method == "POST" and active_tab == "upload":
        upload_form = ExcelUploadForm(
            request.POST,
            request.FILES,
            request_user=request.user,
        )
        if upload_form.is_valid():
            upload = create_excel_upload(upload_form, request.user)
            messages.success(
                request,
                "Contribution file uploaded and validated successfully.",
            )
            return redirect("web_excel_upload_detail", upload_id=upload.id)

    contributions = _scope_to_user_church(
        Contribution.objects.select_related(
            "church",
            "member",
            "member__user",
            "financial_year",
            "contribution_week",
            "category",
            "posted_by",
        ).order_by("-contribution_date", "-created_at"),
        request.user,
    )
    filter_form = ContributionFilterForm(
        request.GET or None,
        request_user=request.user,
    )
    has_active_filters = False
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        query = filters["q"].strip()
        if query:
            contributions = contributions.filter(
                Q(member__user__full_name__icontains=query)
                | Q(bahasha_number__icontains=query)
                | Q(reference_number__icontains=query)
            )
        if filters["church"]:
            contributions = contributions.filter(church=filters["church"])
        if filters["financial_year"]:
            contributions = contributions.filter(
                financial_year=filters["financial_year"]
            )
        if filters["contribution_week"]:
            contributions = contributions.filter(
                contribution_week=filters["contribution_week"]
            )
        if filters["category"]:
            contributions = contributions.filter(category=filters["category"])
        if filters["status"]:
            contributions = contributions.filter(status=filters["status"])
        has_active_filters = any(filters.values())

    contributions = paginate_queryset(
        request,
        contributions,
        page_parameter="contribution_page",
    )

    uploads = _scope_to_user_church(
        ExcelUpload.objects.select_related(
            "church",
            "financial_year",
            "contribution_week",
            "selected_category",
            "uploaded_by",
            "approved_by",
        ).order_by("-uploaded_at"),
        request.user,
    )
    upload_summary = uploads.aggregate(
        total=Count("id"),
        amount=Sum("total_amount", default=0),
    )
    uploads = paginate_queryset(
        request,
        uploads,
        page_parameter="upload_page",
    )

    return render(
        request,
        "contributions/list.html",
        {
            "active_tab": active_tab,
            "contribution_form": contribution_form,
            "contribution_filter_form": filter_form,
            "contributions": contributions,
            "has_active_contribution_filters": has_active_filters,
            "upload_form": upload_form,
            "uploads": uploads,
            "upload_summary": upload_summary,
        },
    )


@login_required(login_url="login")
def contribution_create(request):
    if request.method == "POST":
        form = ContributionForm(request.POST, request_user=request.user)

        if form.is_valid():
            _save_manual_contribution(form, request.user)

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
