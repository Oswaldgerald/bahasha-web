from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from annual_targets.models import MemberAnnualTarget
from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from financial_years.models import FinancialYear
from members.models import Member


@login_required(login_url="login")
def contribution_summary_report(request):
    church_id = request.GET.get("church")
    financial_year_id = request.GET.get("financial_year")
    category_id = request.GET.get("category")

    targets = MemberAnnualTarget.objects.select_related(
        "member",
        "member__user",
        "church",
        "financial_year",
        "category",
    ).all()

    if church_id:
        targets = targets.filter(church_id=church_id)

    if financial_year_id:
        targets = targets.filter(financial_year_id=financial_year_id)

    if category_id:
        targets = targets.filter(category_id=category_id)

    summary = list(
        targets.values("category__name")
        .annotate(
            total_target=Sum("target_amount"),
            total_contributed=Sum("contributed_amount"),
            total_remaining=Sum("remaining_amount"),
        )
        .order_by("category__name")
    )

    for item in summary:
        total_target = item["total_target"] or 0
        total_contributed = item["total_contributed"] or 0

        if total_target > 0:
            item["completion_percentage"] = round(
                (total_contributed / total_target) * 100, 2
            )
        else:
            item["completion_percentage"] = 0

    churches = Church.objects.filter(is_active=True)
    financial_years = FinancialYear.objects.all()
    categories = ContributionCategory.objects.filter(is_active=True)

    return render(
        request,
        "reports/contribution_summary.html",
        {
            "summary": summary,
            "churches": churches,
            "financial_years": financial_years,
            "categories": categories,
            "selected_church": church_id,
            "selected_financial_year": financial_year_id,
            "selected_category": category_id,
        },
    )


@login_required(login_url="login")
def member_statement_report(request):
    member_id = request.GET.get("member")

    members = Member.objects.select_related("user", "church", "jumuiya").all()

    selected_member = None
    targets = []
    contributions = []
    total_contributed = 0

    if member_id:
        selected_member = get_object_or_404(
            Member.objects.select_related("user", "church", "jumuiya"), id=member_id
        )

        targets = MemberAnnualTarget.objects.filter(
            member=selected_member
        ).select_related("category", "financial_year")

        contributions = (
            Contribution.objects.filter(member=selected_member, status="POSTED")
            .select_related("category", "contribution_week", "financial_year")
            .order_by("-contribution_date")
        )

        total_contributed = (
            contributions.aggregate(total=models.Sum("amount"))["total"] or 0
        )

    return render(
        request,
        "reports/member_statement.html",
        {
            "members": members,
            "selected_member": selected_member,
            "targets": targets,
            "contributions": contributions,
            "total_contributed": total_contributed,
            "selected_member_id": member_id,
        },
    )


@login_required(login_url="login")
def weekly_collection_report(request):
    week_id = request.GET.get("week")

    weeks = ContributionWeek.objects.select_related(
        "church", "financial_year"
    ).order_by("-sunday_date")

    selected_week = None
    summary = []
    grand_total = 0

    if week_id:
        selected_week = get_object_or_404(ContributionWeek, id=week_id)

        summary = (
            Contribution.objects.filter(
                contribution_week=selected_week, status="POSTED"
            )
            .values("category__name")
            .annotate(total_amount=Sum("amount"))
            .order_by("category__name")
        )

        grand_total = (
            Contribution.objects.filter(
                contribution_week=selected_week, status="POSTED"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

    return render(
        request,
        "reports/weekly_collection.html",
        {
            "weeks": weeks,
            "selected_week": selected_week,
            "summary": summary,
            "grand_total": grand_total,
            "selected_week_id": week_id,
        },
    )
