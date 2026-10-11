from django.conf import settings
from django.db import models
from django.db.models import Q


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="appointments"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        limit_choices_to={"role": "doctor"},
    )
    date = models.DateField()
    time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date", "time"],
                condition=~Q(status="cancelled"),
                name="unique_active_doctor_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient.full_name} with {self.doctor.doctor_label} on {self.date} {self.time:%H:%M}"
