from django.db.models import Sum
from django.shortcuts import render

from annual_targets.models import MemberAnnualTarget
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from financial_years.models import FinancialYear
from members.models import Member
from web.access import scope_queryset_to_church, staff_dashboard_required


@staff_dashboard_required
def dashboard(request):
    targets = scope_queryset_to_church(MemberAnnualTarget.objects.all(), request.user)
    contributions = scope_queryset_to_church(
        Contribution.objects.all(), request.user
    )
    uploads = scope_queryset_to_church(ExcelUpload.objects.all(), request.user)
    members = scope_queryset_to_church(Member.objects.all(), request.user)
    years = scope_queryset_to_church(FinancialYear.objects.all(), request.user)
    weeks = scope_queryset_to_church(ContributionWeek.objects.all(), request.user)
    churches = scope_queryset_to_church(
        Church.objects.all(), request.user, church_field="pk"
    )
    total_target = (
        targets.aggregate(total=Sum("target_amount"))["total"] or 0
    )

    total_contributed = (
        contributions.filter(status="POSTED").aggregate(total=Sum("amount"))["total"]
        or 0
    )

    if total_target > 0:
        overall_completion = round((total_contributed / total_target) * 100, 2)
    else:
        overall_completion = 0
    category_performance = list(
        targets.values("category__name")
        .annotate(
            total_target=Sum("target_amount"),
            total_contributed=Sum("contributed_amount"),
            total_remaining=Sum("remaining_amount"),
        )
        .order_by("category__name")
    )
    for item in category_performance:
        target = item["total_target"] or 0
        contributed = item["total_contributed"] or 0

        if target > 0:
            item["completion_percentage"] = round((contributed / target) * 100, 2)
        else:
            item["completion_percentage"] = 0

    recent_uploads = uploads.select_related(
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
    ).order_by("-uploaded_at")[:5]

    recent_contributions = contributions.select_related(
        "member",
        "member__user",
        "category",
        "contribution_week",
    ).order_by("-created_at")[:5]

    context = {
        "total_churches": churches.count(),
        "total_members": members.count(),
        "approved_members": members.filter(approval_status="APPROVED").count(),
        "pending_members": members.filter(approval_status="PENDING").count(),
        "total_contributions": contributions.filter(status="POSTED").count(),
        "total_contributed": total_contributed,
        "total_target": total_target,
        "overall_completion": overall_completion,
        "total_uploads": uploads.count(),
        "pending_uploads": uploads.filter(
            status="PENDING_VALIDATION"
        ).count(),
        "failed_uploads": uploads.filter(status="FAILED").count(),
        "active_year": years.filter(is_active=True).first(),
        "active_week": weeks.filter(is_active=True).first(),
        "recent_uploads": recent_uploads,
        "recent_contributions": recent_contributions,
        "category_performance": category_performance,
    }

    return render(request, "dashboard/index.html", context)
