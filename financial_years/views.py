from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from financial_years.models import FinancialYear
from web.forms import FinancialYearForm
from web.pagination import paginate_queryset
from web.access import finance_management_required, scope_queryset_to_church


@finance_management_required
def financial_year_list(request):
    financial_years = FinancialYear.objects.select_related("church").order_by(
        "-year", "church__church_name"
    )
    financial_years = scope_queryset_to_church(financial_years, request.user)
    financial_years = paginate_queryset(request, financial_years)

    return render(
        request, "financial_years/list.html", {"financial_years": financial_years}
    )


@finance_management_required
def financial_year_create(request):
    if request.method == "POST":
        form = FinancialYearForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Financial year created successfully.")
            return redirect("web_financial_years")
    else:
        form = FinancialYearForm(request_user=request.user)

    return render(request, "financial_years/create.html", {"form": form})


@finance_management_required
def financial_year_edit(request, financial_year_id):
    financial_year = get_object_or_404(
        scope_queryset_to_church(FinancialYear.objects.all(), request.user),
        id=financial_year_id,
    )

    if request.method == "POST":
        form = FinancialYearForm(
            request.POST, instance=financial_year, request_user=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Financial year updated successfully.")
            return redirect("web_financial_years")
    else:
        form = FinancialYearForm(instance=financial_year, request_user=request.user)

    return render(
        request,
        "financial_years/edit.html",
        {"form": form, "financial_year": financial_year},
    )
