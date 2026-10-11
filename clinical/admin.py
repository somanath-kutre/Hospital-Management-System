from django.contrib import admin

from .models import Bed, Encounter, Prescription, PrescriptionItem, Treatment, Ward


class BedInline(admin.TabularInline):
    model = Bed
    extra = 1


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    inlines = [BedInline]


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("__str__", "daily_charge", "is_occupied")
    list_filter = ("ward", "is_occupied")


class TreatmentInline(admin.TabularInline):
    model = Treatment
    extra = 0


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("ref_no", "patient", "doctor", "visit_type", "status", "admitted_at")
    list_filter = ("visit_type", "status")
    search_fields = ("ref_no", "patient__first_name", "patient__last_name", "patient__code")
    inlines = [TreatmentInline]


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "encounter", "doctor", "created_at")
    inlines = [PrescriptionItemInline]
