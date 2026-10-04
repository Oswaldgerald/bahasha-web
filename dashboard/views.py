from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from annual_targets.models import MemberAnnualTarget
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from financial_years.models import FinancialYear
from members.models import Member


@login_required(login_url="login")
def dashboard(request):
    total_target = (
        MemberAnnualTarget.objects.aggregate(total=Sum("target_amount"))["total"] or 0
    )

    total_contributed = (
        Contribution.objects.filter(status="POSTED").aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    if total_target > 0:
        overall_completion = round((total_contributed / total_target) * 100, 2)
    else:
        overall_completion = 0
    category_performance = list(
        MemberAnnualTarget.objects.values("category__name")
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

    recent_uploads = ExcelUpload.objects.select_related(
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
    ).order_by("-uploaded_at")[:5]

    recent_contributions = Contribution.objects.select_related(
        "member",
        "member__user",
        "category",
        "contribution_week",
    ).order_by("-created_at")[:5]

    context = {
        "total_churches": Church.objects.count(),
        "total_members": Member.objects.count(),
        "approved_members": Member.objects.filter(approval_status="APPROVED").count(),
        "pending_members": Member.objects.filter(approval_status="PENDING").count(),
        "total_contributions": Contribution.objects.filter(status="POSTED").count(),
        "total_contributed": total_contributed,
        "total_target": total_target,
        "overall_completion": overall_completion,
        "total_uploads": ExcelUpload.objects.count(),
        "pending_uploads": ExcelUpload.objects.filter(
            status="PENDING_VALIDATION"
        ).count(),
        "failed_uploads": ExcelUpload.objects.filter(status="FAILED").count(),
        "active_year": FinancialYear.objects.filter(is_active=True).first(),
        "active_week": ContributionWeek.objects.filter(is_active=True).first(),
        "recent_uploads": recent_uploads,
        "recent_contributions": recent_contributions,
        "category_performance": category_performance,
    }

    return render(request, "dashboard/index.html", context)
