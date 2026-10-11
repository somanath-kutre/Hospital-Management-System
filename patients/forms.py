from django import forms

from accounts.forms import BootstrapModelForm

from .models import Patient


class PatientForm(BootstrapModelForm):
    create_login = forms.BooleanField(
        required=False,
        label="Create a portal login for this patient",
        help_text="A username and temporary password will be shown once after saving.",
    )

    class Meta:
        model = Patient
        exclude = ("user",)
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "address": forms.Textarea(attrs={"rows": 2}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "chronic_conditions": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, creating=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not creating:
            del self.fields["create_login"]
