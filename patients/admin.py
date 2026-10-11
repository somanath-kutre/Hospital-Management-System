from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "gender", "phone", "created_at")
    search_fields = ("code", "first_name", "last_name", "phone")
    list_filter = ("gender", "blood_group")
