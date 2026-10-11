from datetime import date

from django.conf import settings
from django.db import models


class Patient(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    BLOOD_CHOICES = [(b, b) for b in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient",
    )
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"PT{self.pk:06d}"
            super().save(update_fields=["code"])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def __str__(self):
        return f"{self.full_name} ({self.code})"
