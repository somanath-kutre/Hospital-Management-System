from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "date", "time", "status")
    list_filter = ("status", "date", "doctor")
    search_fields = ("patient__first_name", "patient__last_name", "patient__code")
