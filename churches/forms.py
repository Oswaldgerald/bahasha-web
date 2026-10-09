from django import forms

from .models import Church, ChurchGroup


class ChurchGroupForm(forms.ModelForm):
    class Meta:
        model = ChurchGroup
        fields = ["church", "name", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        churches = Church.objects.filter(is_active=True)
        if request_user and not request_user.is_superuser:
            if request_user.church_id:
                churches = churches.filter(id=request_user.church_id)
                self.fields["church"].initial = request_user.church_id
            else:
                churches = churches.none()
        self.fields["church"].queryset = churches

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        church = self.cleaned_data.get("church")
        groups = ChurchGroup.objects.filter(church=church, name__iexact=name)
        if self.instance.pk:
            groups = groups.exclude(pk=self.instance.pk)
        if groups.exists():
            raise forms.ValidationError("This church group already exists.")
        return name
