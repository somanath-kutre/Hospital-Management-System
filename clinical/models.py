from django.conf import settings
from django.db import models
from django.utils import timezone


class Ward(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="beds")
    number = models.CharField(max_length=10)
    daily_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ("ward", "number")
        ordering = ["ward__name", "number"]

    def __str__(self):
        return f"{self.ward.name} / Bed {self.number}"


class Encounter(models.Model):
    """One hospital visit: an OPD consultation or an IPD admission."""

    class Type(models.TextChoices):
        OPD = "OPD", "OPD (outpatient)"
        IPD = "IPD", "IPD (admitted)"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed / Discharged"

    ref_no = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="encounters"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="encounters",
        limit_choices_to={"role": "doctor"},
    )
    visit_type = models.CharField(max_length=3, choices=Type.choices, default=Type.OPD)
    appointment = models.OneToOneField(
        "appointments.Appointment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="encounter",
    )
    admitted_at = models.DateTimeField(default=timezone.now)
    discharged_at = models.DateTimeField(null=True, blank=True)
    bed = models.ForeignKey(Bed, null=True, blank=True, on_delete=models.SET_NULL, related_name="encounters")
    chief_complaint = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Clinical notes / examination findings")
    discharge_summary = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-admitted_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.ref_no:
            self.ref_no = f"{self.visit_type}{self.pk:06d}"
            super().save(update_fields=["ref_no"])

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def stay_days(self):
        end = self.discharged_at or timezone.now()
        return max(1, (end.date() - self.admitted_at.date()).days)

    def close(self, summary=""):
        self.status = self.Status.CLOSED
        self.discharged_at = timezone.now()
        if summary:
            self.discharge_summary = summary
        self.save()
        if self.bed_id:
            Bed.objects.filter(pk=self.bed_id).update(is_occupied=False)

    def __str__(self):
        return f"{self.ref_no} - {self.patient.full_name}"


class Treatment(models.Model):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="treatments")
    date = models.DateTimeField(default=timezone.now)
    title = models.CharField(max_length=150, help_text="e.g. Wound dressing, ECG, IV fluids")
    description = models.TextField(blank=True)
    charge = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.title


class Prescription(models.Model):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="prescriptions")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    advice = models.TextField(blank=True, help_text="Diet, rest, follow-up advice")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rx #{self.pk} for {self.encounter.patient.full_name}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    medicine = models.CharField(max_length=150)
    dosage = models.CharField(max_length=60, help_text="e.g. 500 mg")
    frequency = models.CharField(max_length=60, help_text="e.g. 1-0-1, twice daily")
    duration = models.CharField(max_length=60, help_text="e.g. 5 days")
    instructions = models.CharField(max_length=200, blank=True, help_text="e.g. after food")

    def __str__(self):
        return self.medicine
