from django import forms
from django.utils import timezone

from accounts.forms import BootstrapModelForm
from accounts.models import User
from accounts.permissions import PATIENT

from .models import Appointment


class AppointmentForm(BootstrapModelForm):
    class Meta:
        model = Appointment
        fields = ["patient", "doctor", "date", "time", "reason"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        doctors = User.objects.filter(role=User.Role.DOCTOR, is_active=True).select_related(
            "doctor_profile"
        )
        self.fields["doctor"].queryset = doctors
        self.fields["doctor"].label_from_instance = lambda u: (
            f"{u.doctor_label} - {u.doctor_profile.specialization}"
            if hasattr(u, "doctor_profile")
            else u.doctor_label
        )
        if user is not None and user.role == PATIENT:
            del self.fields["patient"]

    def clean(self):
        cleaned = super().clean()
        day, time, doctor = cleaned.get("date"), cleaned.get("time"), cleaned.get("doctor")
        now = timezone.localtime()
        if day:
            if day < now.date():
                raise forms.ValidationError("The appointment date cannot be in the past.")
            if time and day == now.date() and time < now.time():
                raise forms.ValidationError("That time has already passed today.")
        if day and time and doctor:
            clash = Appointment.objects.filter(doctor=doctor, date=day, time=time).exclude(
                status=Appointment.Status.CANCELLED
            )
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError("This doctor already has an appointment at that time.")
        return cleaned
