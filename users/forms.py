from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from churches.models import Church

from .models import User
from .phone_numbers import country_code_field, normalize_phone_number, split_phone_number
from .profile_pictures import validate_profile_picture


class PhoneNumberFormMixin:
    phone_country_code = country_code_field()

    def _set_phone_initial(self):
        if self.is_bound or not getattr(self.instance, "phone_number", ""):
            return
        code, local_number = split_phone_number(self.instance.phone_number)
        self.fields["phone_country_code"].initial = code
        self.fields["phone_number"].initial = local_number

    def clean_phone_number(self):
        phone_number = normalize_phone_number(
            self.cleaned_data.get("phone_country_code"),
            self.cleaned_data.get("phone_number"),
        )
        queryset = User.objects.filter(
            phone_number__in=[phone_number, phone_number.removeprefix("+")]
        )
        if getattr(self.instance, "pk", None):
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Phone number already exists.")
        return phone_number


class UserForm(PhoneNumberFormMixin, forms.ModelForm):
    phone_country_code = country_code_field()

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        self._set_phone_initial()
        churches = Church.objects.filter(is_active=True)
        if request_user and not request_user.is_superuser:
            if request_user.church_id:
                churches = churches.filter(pk=request_user.church_id)
                self.fields["church"].initial = request_user.church_id
            else:
                churches = churches.none()
        self.fields["church"].queryset = churches

    class Meta:
        model = User
        fields = [
            "username",
            "full_name",
            "phone_country_code",
            "phone_number",
            "church",
            "role",
            "is_active",
        ]


class UserCreateForm(UserForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Create a secure password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Enter the password again",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
            return cleaned_data

        if password1:
            candidate_user = User(
                username=cleaned_data.get("username", ""),
                full_name=cleaned_data.get("full_name", ""),
                phone_number=cleaned_data.get("phone_number", ""),
            )
            try:
                validate_password(password1, user=candidate_user)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(PhoneNumberFormMixin, forms.ModelForm):
    phone_country_code = country_code_field()
    remove_picture = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_picture_name = (
            self.instance.profile_picture.name
            if self.instance and self.instance.profile_picture
            else ""
        )
        self._set_phone_initial()

    def clean_profile_picture(self):
        return validate_profile_picture(
            self.cleaned_data.get("profile_picture"),
            self.instance.profile_picture,
        )

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
            "phone_country_code",
            "phone_number",
        ]
        widgets = {
            "profile_picture": forms.FileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "class": "profile-file-input",
                }
            ),
        }
