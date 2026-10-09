from django import forms

from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear

from .models import Contribution


class ContributionFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.SearchInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "Search member, Bahasha, or reference",
            }
        ),
    )
    financial_year = forms.ModelChoiceField(
        queryset=FinancialYear.objects.none(),
        required=False,
        empty_label="All financial years",
    )
    contribution_week = forms.ModelChoiceField(
        queryset=ContributionWeek.objects.none(),
        required=False,
        empty_label="All contribution weeks",
    )
    category = forms.ModelChoiceField(
        queryset=ContributionCategory.objects.none(),
        required=False,
        empty_label="All categories",
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *Contribution.STATUS_CHOICES],
    )

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)

        years = FinancialYear.objects.select_related("church").order_by("-year")
        weeks = ContributionWeek.objects.select_related(
            "church",
            "financial_year",
        ).order_by("-sunday_date")
        categories = ContributionCategory.objects.select_related("church").order_by(
            "display_order",
            "name",
        )

        if request_user and request_user.church_id and not request_user.is_superuser:
            church_id = request_user.church_id
            years = years.filter(church_id=church_id)
            weeks = weeks.filter(church_id=church_id)
            categories = categories.filter(church_id=church_id)

        financial_year_id = (
            self.data.get("financial_year") if self.is_bound else None
        )
        if financial_year_id:
            weeks = weeks.filter(financial_year_id=financial_year_id)

        self.fields["financial_year"].queryset = years
        self.fields["contribution_week"].queryset = weeks
        self.fields["category"].queryset = categories

        searchable_fields = {
            "financial_year": "Search financial years",
            "contribution_week": "Search week or date",
            "category": "Search categories",
            "status": "Search statuses",
        }
        for field_name, placeholder in searchable_fields.items():
            self.fields[field_name].widget.attrs.update(
                {
                    "data-searchable": "true",
                    "data-search-placeholder": placeholder,
                }
            )
