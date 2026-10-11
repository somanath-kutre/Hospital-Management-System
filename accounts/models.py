from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        DOCTOR = "doctor", "Doctor"
        RECEPTION = "reception", "Receptionist"
        PATIENT = "patient", "Patient"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def doctor_label(self):
        return f"Dr. {self.display_name}"

    def __str__(self):
        return self.display_name


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile"
    )
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150, blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    room = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.doctor_label} ({self.specialization})"
