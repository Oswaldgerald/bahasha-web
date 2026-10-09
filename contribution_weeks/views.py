from datetime import timedelta

from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from contribution_weeks.models import ContributionWeek
from web.forms import ContributionWeekForm
from web.forms import GenerateWeeksForm
from web.pagination import paginate_queryset
from web.access import finance_management_required, scope_queryset_to_church


@finance_management_required
def contribution_week_list(request):
    today = timezone.localdate()
    current_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    weeks = ContributionWeek.objects.select_related(
        "church", "financial_year"
    ).annotate(
        list_priority=Case(
            When(is_active=True, then=Value(0)),
            When(sunday_date=current_sunday, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by(
        "list_priority",
        "-sunday_date",
        "-week_number",
        "church__church_name",
    )
    weeks = scope_queryset_to_church(weeks, request.user)
    weeks = paginate_queryset(request, weeks)

    return render(request, "contribution_weeks/list.html", {"weeks": weeks})


@finance_management_required
def contribution_week_create(request):
    if request.method == "POST":
        form = ContributionWeekForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week created successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm(request_user=request.user)

    return render(request, "contribution_weeks/create.html", {"form": form})


@finance_management_required
def contribution_week_edit(request, week_id):
    week = get_object_or_404(
        scope_queryset_to_church(ContributionWeek.objects.all(), request.user),
        id=week_id,
    )

    if request.method == "POST":
        form = ContributionWeekForm(
            request.POST, instance=week, request_user=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week updated successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm(instance=week, request_user=request.user)

    return render(request, "contribution_weeks/edit.html", {"form": form, "week": week})


@finance_management_required
@require_POST
def contribution_week_activate(request, week_id):
    week = get_object_or_404(
        scope_queryset_to_church(ContributionWeek.objects.all(), request.user),
        id=week_id,
    )
    week.is_active = True
    week.is_closed = False
    week.save()

    messages.success(request, f"Week {week.week_number} activated successfully.")
    return redirect("web_contribution_weeks")


@finance_management_required
@require_POST
def contribution_week_close(request, week_id):
    week = get_object_or_404(
        scope_queryset_to_church(ContributionWeek.objects.all(), request.user),
        id=week_id,
    )
    week.is_closed = True
    week.is_active = False
    week.save()

    messages.success(request, f"Week {week.week_number} closed successfully.")
    return redirect("web_contribution_weeks")


@finance_management_required
def contribution_week_generate(request):
    if request.method == "POST":
        form = GenerateWeeksForm(request.POST, request_user=request.user)

        if form.is_valid():
            church = form.cleaned_data["church"]
            financial_year = form.cleaned_data["financial_year"]

            start_date = financial_year.start_date
            end_date = financial_year.end_date

            current_date = start_date

            while current_date.weekday() != 6:
                current_date += timedelta(days=1)

            week_number = 1
            created_count = 0

            while current_date <= end_date:
                week, created = ContributionWeek.objects.get_or_create(
                    church=church,
                    financial_year=financial_year,
                    week_number=week_number,
                    defaults={
                        "sunday_date": current_date,
                        "is_active": False,
                        "is_closed": False,
                    },
                )

                if created:
                    created_count += 1

                week_number += 1
                current_date += timedelta(days=7)

            messages.success(
                request, f"{created_count} contribution weeks generated successfully."
            )

            return redirect("web_contribution_weeks")
    else:
        form = GenerateWeeksForm(request_user=request.user)

    return render(request, "contribution_weeks/generate.html", {"form": form})
