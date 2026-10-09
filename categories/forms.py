from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from churches.models import Church

from .models import ContributionCategory


class ContributionCategoryForm(forms.ModelForm):
    class Meta:
        model = ContributionCategory
        fields = [
            "church",
            "name",
            "name_sw",
            "key",
            "code",
            "description",
            "frequency",
            "icon_key",
            "theme_color",
            "display_order",
            "suggested_amount",
            "minimum_amount",
            "maximum_amount",
            "is_mobile_visible",
            "allows_member_payment",
            "allows_catch_up",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "theme_color": forms.TextInput(attrs={"type": "color", "data-native-input": "true"}),
            "suggested_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "minimum_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "maximum_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }
        help_texts = {
            "key": "Stable mobile identifier. It cannot change after financial records exist.",
            "name_sw": "Optional Swahili label shown in the mobile app.",
            "theme_color": "Card color used by the mobile application.",
            "allows_catch_up": "Allow members to settle eligible past contribution weeks.",
        }

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_user = request_user
        churches = Church.objects.filter(is_active=True).order_by("church_name")
        if request_user and not request_user.is_superuser:
            if request_user.church_id:
                churches = churches.filter(id=request_user.church_id)
                self.fields["church"].initial = request_user.church_id
            else:
                churches = churches.none()
        self.fields["church"].queryset = churches
        self.fields["key"].required = False

    def clean_church(self):
        church = self.cleaned_data["church"]
        if (
            self.request_user
            and self.request_user.church_id
            and not self.request_user.is_superuser
            and church.id != self.request_user.church_id
        ):
            raise ValidationError("You can manage categories only for your church.")
        return church

    def clean_key(self):
        key = slugify(
            self.cleaned_data.get("key")
            or self.cleaned_data.get("code")
            or self.cleaned_data.get("name")
        )
        if not key:
            raise ValidationError("Enter a category key or a name that can generate one.")

        if self.instance.pk and key != self.instance.key:
            has_financial_records = (
                self.instance.contributions.exists()
                or self.instance.annual_targets.exists()
                or self.instance.excel_uploads.exists()
            )
            if has_financial_records:
                raise ValidationError("The key cannot change after financial records exist.")
        return key

    def clean_code(self):
        code = self.cleaned_data.get("code")
        return code.strip().upper() if code else None
