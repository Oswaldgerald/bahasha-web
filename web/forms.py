from django import forms
from churches.models import Church
from jumuiya.models import Jumuiya
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from annual_targets.models import MemberAnnualTarget
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from notifications.models import Notification
from users.models import User


# Jumuiya Management Forms


class JumuiyaForm(forms.ModelForm):
    """Edit a Jumuiya with church choices scoped to the requesting user."""

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope church choices for the requesting user."""

        super().__init__(*args, **kwargs)
        scope_church_field(self, request_user)

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


class FinancialYearForm(forms.ModelForm):
    """Edit financial years using only churches visible to the requester."""

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope financial-year church choices for the requesting user."""

        super().__init__(*args, **kwargs)
        scope_church_field(self, request_user)

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
    """Edit one contribution week with scoped church and year choices."""

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope church and financial-year choices consistently."""

        super().__init__(*args, **kwargs)
        scope_church_field(self, request_user)
        scope_related_field(self, "financial_year", request_user)

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
    """Collect and validate a date range used to generate weekly periods."""

    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True))

    financial_year = forms.ModelChoiceField(queryset=FinancialYear.objects.all())

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope the generation form's financial year choices."""

        super().__init__(*args, **kwargs)
        scope_church_field(self, request_user)
        scope_related_field(self, "financial_year", request_user)

    def clean(self):
        """Ensure the requested generation range is chronological and in-year."""

        cleaned_data = super().clean()
        church = cleaned_data.get("church")
        financial_year = cleaned_data.get("financial_year")
        if church and financial_year and financial_year.church_id != church.id:
            self.add_error(
                "financial_year",
                "Financial year must belong to the selected church.",
            )
        return cleaned_data


class MemberAnnualTargetForm(forms.ModelForm):
    """Edit a member target with church-scoped related choices."""

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

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope all target relationships to the requesting user's church."""

        super().__init__(*args, **kwargs)
        scope_financial_form_fields(self, request_user)


class ContributionForm(forms.ModelForm):
    """Edit contribution details using only authorized financial records."""

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

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope contribution relationships and apply shared widget styling."""

        super().__init__(*args, **kwargs)
        scope_financial_form_fields(self, request_user)


# Excel Upload Form
class ExcelUploadForm(forms.ModelForm):
    """Collect contribution workbook context and validate the uploaded file."""

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

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope upload context fields to records the user may manage."""

        super().__init__(*args, **kwargs)
        scope_financial_form_fields(self, request_user)

    def clean_file(self):
        """Require a supported Excel workbook within the upload size limit."""

        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Upload an Excel file with the .xlsx extension.")
        if uploaded_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The contribution file must not exceed 5 MB.")
        return uploaded_file


def scope_financial_form_fields(form, request_user):
    """Scope church, period, category, and member choices consistently."""

    if not request_user or request_user.is_superuser:
        return

    if not request_user.church_id:
        if "church" in form.fields:
            form.fields["church"].queryset = Church.objects.none()
        for field_name in {
            "member",
            "financial_year",
            "contribution_week",
            "category",
            "selected_category",
        }.intersection(form.fields):
            field = form.fields[field_name]
            if hasattr(field, "queryset"):
                field.queryset = field.queryset.none()
        return

    church_id = request_user.church_id
    if "church" in form.fields:
        form.fields["church"].queryset = Church.objects.filter(id=church_id)
        form.fields["church"].initial = church_id

    church_scoped_fields = {
        "member",
        "financial_year",
        "contribution_week",
        "category",
        "selected_category",
    }
    for field_name in church_scoped_fields.intersection(form.fields):
        field = form.fields[field_name]
        if hasattr(field, "queryset"):
            field.queryset = field.queryset.filter(church_id=church_id)


def scope_church_field(form, request_user):
    """Restrict a form's church field for non-superusers."""

    if "church" not in form.fields or not request_user or request_user.is_superuser:
        return
    if not request_user.church_id:
        form.fields["church"].queryset = Church.objects.none()
        return
    form.fields["church"].queryset = Church.objects.filter(id=request_user.church_id)
    form.fields["church"].initial = request_user.church_id


def scope_related_field(form, field_name, request_user):
    """Restrict a related model field using its church ownership path."""

    if field_name not in form.fields or not request_user or request_user.is_superuser:
        return
    field = form.fields[field_name]
    if not request_user.church_id:
        field.queryset = field.queryset.none()
        return
    field.queryset = field.queryset.filter(church_id=request_user.church_id)


# Church Management Form
class ChurchForm(forms.ModelForm):
    """Create or edit core church identity and location details."""

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
    """Compose a notification with church choices scoped to the requester."""

    target_role = forms.ChoiceField(
        choices=[("", "All Users")] + list(User.ROLE_CHOICES), required=False
    )

    def __init__(self, *args, request_user=None, **kwargs):
        """Scope notification church choices to the requesting user."""

        super().__init__(*args, **kwargs)
        scope_church_field(self, request_user)

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
