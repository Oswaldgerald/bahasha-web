from django import forms
from django.contrib.auth.password_validation import validate_password

from churches.models import Church, ChurchGroup
from jumuiya.models import Jumuiya
from users.models import User
from users.phone_numbers import (
    country_code_field,
    normalize_phone_number,
    split_phone_number,
)
from users.profile_pictures import validate_profile_picture

from .models import Member
from .services import create_member, update_member


class MemberCsvUploadForm(forms.Form):
    file = forms.FileField(
        label="Member CSV file",
        widget=forms.FileInput(attrs={"accept": ".csv,text/csv"}),
        help_text=(
            "UTF-8 CSV, up to 2 MB and 5,000 member rows. "
            "Faili la CSV lenye hadi washarika 5,000."
        ),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a file with the .csv extension.")
        if uploaded_file.size > 2 * 1024 * 1024:
            raise forms.ValidationError("The CSV file must not exceed 2 MB.")
        return uploaded_file


class MemberBaseForm(forms.Form):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "data-member-photo-input": "true",
            }
        ),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    full_name = forms.CharField(max_length=255)
    phone_country_code = country_code_field()
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "placeholder": "712 345 678"}
        ),
    )
    email = forms.EmailField(required=False)
    church = forms.ModelChoiceField(queryset=Church.objects.filter(is_active=True))
    jumuiya = forms.ModelChoiceField(
        queryset=Jumuiya.objects.filter(is_active=True),
        required=False,
    )
    church_groups = forms.ModelMultipleChoiceField(
        queryset=ChurchGroup.objects.filter(is_active=True),
        required=False,
    )
    bahasha_number = forms.CharField(max_length=100)
    gender = forms.ChoiceField(
        choices=[("", "Select Gender")] + Member.GENDER_CHOICES,
        required=False,
    )
    marital_status = forms.ChoiceField(
        choices=[("", "Select Marital Status")] + Member.MARITAL_STATUS_CHOICES,
        required=False,
    )
    demographics = forms.CharField(widget=forms.Textarea, required=False)
    approval_status = forms.ChoiceField(choices=Member.APPROVAL_STATUS)

    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop("member", None)
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        self._scope_relationship_fields()
        self._set_member_initial_values()

    def _selected_church_id(self):
        church_id = self.data.get("church") if self.is_bound else None
        if not church_id and self.member:
            church_id = self.member.church_id
        if (
            not church_id
            and self.request_user
            and self.request_user.church_id
            and not self.request_user.is_superuser
        ):
            church_id = self.request_user.church_id
        return church_id

    def _scope_relationship_fields(self):
        church_queryset = Church.objects.filter(is_active=True)
        if (
            self.request_user
            and self.request_user.church_id
            and not self.request_user.is_superuser
        ):
            church_queryset = church_queryset.filter(id=self.request_user.church_id)
            self.fields["church"].initial = self.request_user.church_id

        self.fields["church"].queryset = church_queryset
        self.fields["church"].widget.attrs["data-member-church"] = "true"
        self.fields["jumuiya"].widget.attrs["data-member-jumuiya"] = "true"
        self.fields["church_groups"].widget.attrs["data-member-groups"] = "true"

        church_id = self._selected_church_id()
        if church_id:
            self.fields["jumuiya"].queryset = Jumuiya.objects.filter(
                church_id=church_id,
                is_active=True,
            )
            self.fields["church_groups"].queryset = ChurchGroup.objects.filter(
                church_id=church_id,
                is_active=True,
            )
        else:
            self.fields["jumuiya"].queryset = Jumuiya.objects.filter(is_active=True)
            self.fields["church_groups"].queryset = ChurchGroup.objects.filter(
                is_active=True
            )

    def _set_member_initial_values(self):
        if not self.member:
            return

        self.fields["username"].initial = self.member.user.username
        self.fields["full_name"].initial = self.member.user.full_name
        phone_code, local_number = split_phone_number(self.member.user.phone_number)
        self.fields["phone_country_code"].initial = phone_code
        self.fields["phone_number"].initial = local_number
        self.fields["email"].initial = self.member.user.email
        self.fields["church"].initial = self.member.church
        self.fields["jumuiya"].initial = self.member.jumuiya
        self.fields["church_groups"].initial = self.member.church_groups.all()
        self.fields["bahasha_number"].initial = self.member.bahasha_number
        self.fields["gender"].initial = self.member.gender
        self.fields["marital_status"].initial = self.member.marital_status
        self.fields["demographics"].initial = self.member.demographics
        self.fields["approval_status"].initial = self.member.approval_status

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        queryset = User.objects.filter(username__iexact=username)
        if self.member:
            queryset = queryset.exclude(id=self.member.user_id)
        if queryset.exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_phone_number(self):
        phone_number = normalize_phone_number(
            self.cleaned_data.get("phone_country_code"),
            self.cleaned_data.get("phone_number"),
        )
        queryset = User.objects.filter(
            phone_number__in=[phone_number, phone_number.removeprefix("+")]
        )
        if self.member:
            queryset = queryset.exclude(id=self.member.user_id)
        if queryset.exists():
            raise forms.ValidationError("Phone number already exists.")
        return phone_number

    def clean_profile_picture(self):
        current_picture = self.member.user.profile_picture if self.member else None
        return validate_profile_picture(
            self.cleaned_data.get("profile_picture"),
            current_picture,
        )

    def clean_bahasha_number(self):
        bahasha_number = self.cleaned_data["bahasha_number"].strip().upper()
        queryset = Member.objects.filter(bahasha_number__iexact=bahasha_number)
        if self.member:
            queryset = queryset.exclude(id=self.member.id)
        if queryset.exists():
            raise forms.ValidationError("Bahasha number already exists.")
        return bahasha_number

    def clean(self):
        cleaned_data = super().clean()
        church = cleaned_data.get("church")
        jumuiya = cleaned_data.get("jumuiya")
        church_groups = cleaned_data.get("church_groups")

        if church and jumuiya and jumuiya.church_id != church.id:
            self.add_error("jumuiya", "Jumuiya must belong to the selected church.")
        if church and church_groups:
            invalid_groups = church_groups.exclude(church=church)
            if invalid_groups.exists():
                self.add_error(
                    "church_groups",
                    "All church groups must belong to the selected church.",
                )
        return cleaned_data


class MemberCreateForm(MemberBaseForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    approval_status = forms.ChoiceField(
        choices=Member.APPROVAL_STATUS,
        initial="APPROVED",
    )

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self):
        return create_member(self.cleaned_data)


class MemberEditForm(MemberBaseForm):
    remove_picture = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False)

    def _set_member_initial_values(self):
        super()._set_member_initial_values()
        if self.member:
            self.fields["is_active"].initial = self.member.is_active

    def save(self):
        return update_member(self.member, self.cleaned_data)
