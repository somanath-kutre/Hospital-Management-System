from django import forms
from django.contrib.auth.forms import UserCreationForm

from patients.models import Patient

from .models import DoctorProfile, User


class BootstrapMixin:
    """Adds Bootstrap classes to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class BootstrapModelForm(BootstrapMixin, forms.ModelForm):
    pass


class PatientSignupForm(BootstrapMixin, UserCreationForm):
    """Public self-registration for patients (creates login + patient record)."""

    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(choices=Patient.GENDER_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        user.save()
        Patient.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=self.cleaned_data["date_of_birth"],
            gender=self.cleaned_data["gender"],
            phone=user.phone,
            email=user.email,
        )
        return user


class StaffCreateForm(BootstrapMixin, UserCreationForm):
    """Admin creates doctors / receptionists / other admins."""

    specialization = forms.CharField(required=False, help_text="Required for doctors")
    qualification = forms.CharField(required=False)
    consultation_fee = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=8)
    room = forms.CharField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (v, l) for v, l in User.Role.choices if v != User.Role.PATIENT
        ]
        self.fields["first_name"].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.DOCTOR and not cleaned.get("specialization"):
            self.add_error("specialization", "Specialization is required for doctors.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=True)
        if user.role == User.Role.DOCTOR:
            DoctorProfile.objects.create(
                user=user,
                specialization=self.cleaned_data["specialization"],
                qualification=self.cleaned_data.get("qualification") or "",
                consultation_fee=self.cleaned_data.get("consultation_fee") or 0,
                room=self.cleaned_data.get("room") or "",
            )
        return user
