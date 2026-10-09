from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from contribution_weeks.models import ContributionWeek
from web.forms import ContributionWeekForm
from web.forms import GenerateWeeksForm
from web.pagination import paginate_queryset


@login_required(login_url="login")
def contribution_week_list(request):
    weeks = ContributionWeek.objects.select_related(
        "church", "financial_year"
    ).order_by("-sunday_date", "-week_number", "church__church_name")
    weeks = paginate_queryset(request, weeks)

    return render(request, "contribution_weeks/list.html", {"weeks": weeks})


@login_required(login_url="login")
def contribution_week_create(request):
    if request.method == "POST":
        form = ContributionWeekForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week created successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm()

    return render(request, "contribution_weeks/create.html", {"form": form})


@login_required(login_url="login")
def contribution_week_edit(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)

    if request.method == "POST":
        form = ContributionWeekForm(request.POST, instance=week)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week updated successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm(instance=week)

    return render(request, "contribution_weeks/edit.html", {"form": form, "week": week})


@login_required(login_url="login")
@require_POST
def contribution_week_activate(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)
    week.is_active = True
    week.is_closed = False
    week.save()

    messages.success(request, f"Week {week.week_number} activated successfully.")
    return redirect("web_contribution_weeks")


@login_required(login_url="login")
@require_POST
def contribution_week_close(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)
    week.is_closed = True
    week.is_active = False
    week.save()

    messages.success(request, f"Week {week.week_number} closed successfully.")
    return redirect("web_contribution_weeks")


@login_required(login_url="login")
def contribution_week_generate(request):
    if request.method == "POST":
        form = GenerateWeeksForm(request.POST)

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
        form = GenerateWeeksForm()

    return render(request, "contribution_weeks/generate.html", {"form": form})
