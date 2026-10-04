from django import forms
from django.contrib.auth.password_validation import validate_password
from users.models import User
from churches.models import Church
from jumuiya.models import Jumuiya
from members.models import Member
from members.services import create_member, update_member
from categories.models import ContributionCategory
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from annual_targets.models import MemberAnnualTarget
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from notifications.models import Notification



#User Management Forms
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "full_name",
            "phone_number",
            "church",
            "role",
            "is_active",
        ]
# Member Management Forms
class MemberCreateForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    full_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True))
    jumuiya = forms.ModelChoiceField(
        queryset=Jumuiya.objects.filter(is_active=True),
        required=False
    )

    bahasha_number = forms.CharField(max_length=100)
    gender = forms.ChoiceField(
        choices=[("", "Select Gender")] + Member.GENDER_CHOICES,
        required=False
    )
    demographics = forms.CharField(
        widget=forms.Textarea,
        required=False
    )
    approval_status = forms.ChoiceField(
        choices=Member.APPROVAL_STATUS,
        initial="APPROVED"
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        self._scope_relationship_fields()

    def _scope_relationship_fields(self):
        church_queryset = Church.objects.filter(is_active=True)
        if self.request_user and self.request_user.church_id and not self.request_user.is_superuser:
            church_queryset = church_queryset.filter(id=self.request_user.church_id)
        self.fields["church"].queryset = church_queryset
        self.fields["church"].widget.attrs["data-member-church"] = "true"
        self.fields["jumuiya"].widget.attrs["data-member-jumuiya"] = "true"

        church_id = self.data.get("church") if self.is_bound else None
        if (
            not church_id
            and self.request_user
            and self.request_user.church_id
            and not self.request_user.is_superuser
        ):
            church_id = self.request_user.church_id
            self.fields["church"].initial = church_id

        if church_id:
            self.fields["jumuiya"].queryset = Jumuiya.objects.filter(
                church_id=church_id,
                is_active=True,
            )
        else:
            self.fields["jumuiya"].queryset = Jumuiya.objects.filter(is_active=True)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number already exists.")
        return phone_number

    def clean_bahasha_number(self):
        bahasha_number = self.cleaned_data["bahasha_number"].strip().upper()
        if Member.objects.filter(bahasha_number__iexact=bahasha_number).exists():
            raise forms.ValidationError("Bahasha number already exists.")
        return bahasha_number

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        church = cleaned_data.get("church")
        jumuiya = cleaned_data.get("jumuiya")
        if church and jumuiya and jumuiya.church_id != church.id:
            self.add_error("jumuiya", "Jumuiya must belong to the selected church.")
        return cleaned_data

    def save(self):
        return create_member(self.cleaned_data)

class MemberEditForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    full_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)

    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True))
    jumuiya = forms.ModelChoiceField(
        queryset=Jumuiya.objects.filter(is_active=True),
        required=False
    )

    bahasha_number = forms.CharField(max_length=100)

    gender = forms.ChoiceField(
        choices=[("", "Select Gender")] + Member.GENDER_CHOICES,
        required=False
    )

    demographics = forms.CharField(
        widget=forms.Textarea,
        required=False
    )

    approval_status = forms.ChoiceField(
        choices=Member.APPROVAL_STATUS
    )

    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop("member", None)
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        church_queryset = Church.objects.filter(is_active=True)
        if self.request_user and self.request_user.church_id and not self.request_user.is_superuser:
            church_queryset = church_queryset.filter(id=self.request_user.church_id)
        self.fields["church"].queryset = church_queryset
        self.fields["church"].widget.attrs["data-member-church"] = "true"
        self.fields["jumuiya"].widget.attrs["data-member-jumuiya"] = "true"

        church_id = self.data.get("church") if self.is_bound else None
        if not church_id and self.member:
            church_id = self.member.church_id
        self.fields["jumuiya"].queryset = Jumuiya.objects.filter(
            church_id=church_id,
            is_active=True,
        ) if church_id else Jumuiya.objects.none()

        if self.member:
            self.fields["username"].initial = self.member.user.username
            self.fields["full_name"].initial = self.member.user.full_name
            self.fields["phone_number"].initial = self.member.user.phone_number
            self.fields["email"].initial = self.member.user.email
            self.fields["church"].initial = self.member.church
            self.fields["jumuiya"].initial = self.member.jumuiya
            self.fields["bahasha_number"].initial = self.member.bahasha_number
            self.fields["gender"].initial = self.member.gender
            self.fields["demographics"].initial = self.member.demographics
            self.fields["approval_status"].initial = self.member.approval_status
            self.fields["is_active"].initial = self.member.is_active

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        queryset = User.objects.filter(username__iexact=username)
        if self.member:
            queryset = queryset.exclude(id=self.member.user_id)
        if queryset.exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]

        qs = User.objects.filter(phone_number=phone_number)

        if self.member:
            qs = qs.exclude(id=self.member.user.id)

        if qs.exists():
            raise forms.ValidationError("Phone number already exists.")

        return phone_number

    def clean_bahasha_number(self):
        bahasha_number = self.cleaned_data["bahasha_number"].strip().upper()

        qs = Member.objects.filter(bahasha_number__iexact=bahasha_number)

        if self.member:
            qs = qs.exclude(id=self.member.id)

        if qs.exists():
            raise forms.ValidationError("Bahasha number already exists.")

        return bahasha_number

    def clean(self):
        cleaned_data = super().clean()
        church = cleaned_data.get("church")
        jumuiya = cleaned_data.get("jumuiya")
        if church and jumuiya and jumuiya.church_id != church.id:
            self.add_error("jumuiya", "Jumuiya must belong to the selected church.")
        return cleaned_data

    def save(self):
        return update_member(self.member, self.cleaned_data)

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
    church = forms.ModelChoiceField(
        queryset=Church.objects.filter(is_active=True)
    )

    financial_year = forms.ModelChoiceField(
        queryset=FinancialYear.objects.all()
    )

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
        choices=[("", "All Users")] + list(User.ROLE_CHOICES),
        required=False
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

# Profile form
class ProfileUpdateForm(forms.ModelForm):
    remove_picture = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_picture_name = (
            self.instance.profile_picture.name
            if self.instance and self.instance.profile_picture
            else ""
        )

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        if not picture or picture == self.instance.profile_picture:
            return picture

        if picture.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile picture must be 5 MB or smaller.")

        image_format = getattr(getattr(picture, "image", None), "format", "")
        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Upload a JPEG, PNG, or WebP image.")

        if picture.image.width > 5000 or picture.image.height > 5000:
            raise forms.ValidationError("Image dimensions must not exceed 5000 x 5000 pixels.")

        return picture

    def save(self, commit=True):
        user = super().save(commit=False)
        remove_picture = self.cleaned_data.get("remove_picture", False)
        has_new_picture = "profile_picture" in self.files

        if remove_picture:
            user.profile_picture = None

        if commit:
            user.save()
            if self._original_picture_name and (remove_picture or has_new_picture):
                storage = self.instance._meta.get_field("profile_picture").storage
                if self._original_picture_name != user.profile_picture.name:
                    storage.delete(self._original_picture_name)

        return user

    class Meta:
        model = User
        fields = [
            "profile_picture",
            "full_name",
            "phone_number",
        ]
        widgets = {
            "profile_picture": forms.FileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "profile-file-input",
            }),
        }
