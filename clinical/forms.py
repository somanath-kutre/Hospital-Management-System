from django import forms
from django.forms import inlineformset_factory

from accounts.forms import BootstrapModelForm
from accounts.models import User

from .models import Bed, Encounter, Prescription, PrescriptionItem, Treatment


class EncounterCreateForm(BootstrapModelForm):
    class Meta:
        model = Encounter
        fields = ["patient", "doctor", "visit_type", "bed", "chief_complaint"]
        widgets = {"chief_complaint": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(role=User.Role.DOCTOR, is_active=True)
        self.fields["doctor"].label_from_instance = lambda u: u.doctor_label
        self.fields["bed"].queryset = Bed.objects.filter(is_occupied=False).select_related("ward")
        self.fields["bed"].required = False
        self.fields["bed"].help_text = "Required for IPD admissions (only free beds are listed)."
        if user is not None and user.role == User.Role.DOCTOR:
            self.fields["doctor"].initial = user.pk

    def clean(self):
        cleaned = super().clean()
        vtype, bed = cleaned.get("visit_type"), cleaned.get("bed")
        if vtype == Encounter.Type.IPD and not bed:
            self.add_error("bed", "Select a bed for an IPD admission.")
        if vtype == Encounter.Type.OPD:
            cleaned["bed"] = None
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.visit_type == Encounter.Type.OPD:
            obj.bed = None
        if commit:
            obj.save()
            if obj.bed_id:
                Bed.objects.filter(pk=obj.bed_id).update(is_occupied=True)
        return obj


class EncounterClinicalForm(BootstrapModelForm):
    class Meta:
        model = Encounter
        fields = ["chief_complaint", "diagnosis", "notes"]
        widgets = {f: forms.Textarea(attrs={"rows": 3}) for f in fields}


class DischargeForm(BootstrapModelForm):
    class Meta:
        model = Encounter
        fields = ["discharge_summary"]
        labels = {"discharge_summary": "Summary / closing notes"}
        widgets = {"discharge_summary": forms.Textarea(attrs={"rows": 5})}


class TreatmentForm(BootstrapModelForm):
    class Meta:
        model = Treatment
        fields = ["title", "description", "charge"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class PrescriptionForm(BootstrapModelForm):
    class Meta:
        model = Prescription
        fields = ["advice"]
        widgets = {"advice": forms.Textarea(attrs={"rows": 2})}


class PrescriptionItemForm(BootstrapModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ["medicine", "dosage", "frequency", "duration", "instructions"]


PrescriptionItemFormSet = inlineformset_factory(
    Prescription, PrescriptionItem, form=PrescriptionItemForm, extra=5, can_delete=False
)
