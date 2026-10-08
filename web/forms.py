from django import forms
from churches.models import Church
from jumuiya.models import Jumuiya
from categories.models import ContributionCategory
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from annual_targets.models import MemberAnnualTarget
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from notifications.models import Notification
from users.models import User


# Jumuiya Management Forms


class JumuiyaForm(forms.ModelForm):
    class Meta:
        model = Jumuiya
        fields = [
            "church",
            "name",
            "description",
            "leader_name",
            "is_active",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class ContributionCategoryForm(forms.ModelForm):
    class Meta:
        model = ContributionCategory
        fields = [
            "name",
            "code",
            "description",
            "frequency",
            "display_order",
            "is_annual",
            "is_active",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class FinancialYearForm(forms.ModelForm):
    class Meta:
        model = FinancialYear
        fields = [
            "church",
            "year",
            "start_date",
            "end_date",
            "is_active",
        ]

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ContributionWeekForm(forms.ModelForm):
    class Meta:
        model = ContributionWeek
        fields = [
            "church",
            "financial_year",
            "week_number",
            "sunday_date",
            "is_active",
            "is_closed",
        ]

        widgets = {
            "sunday_date": forms.DateInput(attrs={"type": "date"}),
        }


class GenerateWeeksForm(forms.Form):
    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True))

    financial_year = forms.ModelChoiceField(queryset=FinancialYear.objects.all())


class MemberAnnualTargetForm(forms.ModelForm):
    class Meta:
        model = MemberAnnualTarget
        fields = [
            "member",
            "church",
            "financial_year",
            "category",
            "target_amount",
            "contributed_amount",
        ]


class ContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = [
            "church",
            "member",
            "financial_year",
            "contribution_week",
            "category",
            "amount",
            "contribution_date",
            "status",
            "remarks",
        ]

        widgets = {
            "contribution_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }


# Excel Upload Form
class ExcelUploadForm(forms.ModelForm):
    class Meta:
        model = ExcelUpload
        fields = [
            "church",
            "financial_year",
            "contribution_week",
            "selected_category",
            "file",
        ]
        widgets = {
            "file": forms.FileInput(
                attrs={
                    "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "data-contribution-file-input": "true",
                }
            )
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Upload an Excel file with the .xlsx extension.")
        if uploaded_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The contribution file must not exceed 5 MB.")
        return uploaded_file


# Church Management Form
class ChurchForm(forms.ModelForm):
    class Meta:
        model = Church
        fields = [
            "church_code",
            "church_name",
            "parish",
            "district",
            "location",
            "is_active",
        ]


# Notification Form
class NotificationForm(forms.ModelForm):
    target_role = forms.ChoiceField(
        choices=[("", "All Users")] + list(User.ROLE_CHOICES), required=False
    )

    class Meta:
        model = Notification
        fields = [
            "church",
            "title",
            "message",
            "notification_type",
            "target_role",
        ]

        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }
