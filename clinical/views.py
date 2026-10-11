from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import ADMIN, DOCTOR, FRONT_DESK, RECEPTION, STAFF, role_required

from .forms import (
    DischargeForm,
    EncounterClinicalForm,
    EncounterCreateForm,
    PrescriptionForm,
    PrescriptionItemFormSet,
    TreatmentForm,
)
from .models import Encounter, Prescription


def encounters_for(user):
    """Encounters a user may see: admin/reception all, doctor own, patient own."""
    qs = Encounter.objects.select_related("patient", "doctor", "bed")
    if user.is_superuser or user.role in (ADMIN, RECEPTION):
        return qs
    if user.role == DOCTOR:
        return qs.filter(doctor=user)
    return qs.filter(patient__user=user)


def can_edit_clinical(user, enc):
    return user.is_superuser or user.role == ADMIN or (user.role == DOCTOR and enc.doctor_id == user.id)


@login_required
def encounter_list(request):
    qs = encounters_for(request.user)
    vtype = request.GET.get("type", "")
    status = request.GET.get("status", "")
    if vtype in ("OPD", "IPD"):
        qs = qs.filter(visit_type=vtype)
    if status in ("active", "closed"):
        qs = qs.filter(status=status)
    return render(
        request, "clinical/encounter_list.html", {"encounters": qs[:200], "vtype": vtype, "status": status}
    )


@role_required(ADMIN, RECEPTION, DOCTOR)
def encounter_create(request):
    form = EncounterCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            enc = form.save()
        messages.success(request, f"{enc.get_visit_type_display()} record {enc.ref_no} created.")
        return redirect("encounter_detail", pk=enc.pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": "New OPD visit / IPD admission", "cancel_url": "/clinical/"},
    )


@login_required
def encounter_detail(request, pk):
    user = request.user
    enc = get_object_or_404(encounters_for(user), pk=pk)
    ctx = {
        "enc": enc,
        "treatments": enc.treatments.all(),
        "prescriptions": enc.prescriptions.prefetch_related("items").select_related("doctor"),
        "can_edit": can_edit_clinical(user, enc),
        "can_close": user.is_superuser or user.role in STAFF,
        "can_bill": user.is_superuser or user.role in FRONT_DESK,
    }
    if ctx["can_bill"] or user.role == "patient":
        ctx["invoices"] = enc.invoices.prefetch_related("items", "payments")
    return render(request, "clinical/encounter_detail.html", ctx)


@role_required(ADMIN, DOCTOR)
def encounter_edit(request, pk):
    enc = get_object_or_404(encounters_for(request.user), pk=pk)
    if not can_edit_clinical(request.user, enc):
        raise PermissionDenied
    form = EncounterClinicalForm(request.POST or None, instance=enc)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Clinical details saved.")
        return redirect("encounter_detail", pk=enc.pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": f"Diagnosis & notes - {enc.ref_no}", "cancel_url": f"/clinical/{pk}/"},
    )


@role_required(ADMIN, DOCTOR)
def treatment_add(request, pk):
    enc = get_object_or_404(encounters_for(request.user), pk=pk)
    if not can_edit_clinical(request.user, enc):
        raise PermissionDenied
    if not enc.is_active:
        messages.error(request, "This record is closed.")
        return redirect("encounter_detail", pk=pk)
    form = TreatmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        t.encounter = enc
        t.performed_by = request.user
        t.save()
        messages.success(request, "Treatment recorded.")
        return redirect("encounter_detail", pk=pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": f"Add treatment - {enc.ref_no}", "cancel_url": f"/clinical/{pk}/"},
    )


@role_required(ADMIN, DOCTOR)
def prescription_add(request, pk):
    enc = get_object_or_404(encounters_for(request.user), pk=pk)
    if not can_edit_clinical(request.user, enc):
        raise PermissionDenied
    form = PrescriptionForm(request.POST or None)
    formset = PrescriptionItemFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        filled = [f for f in formset.forms if f.cleaned_data.get("medicine")]
        if not filled:
            messages.error(request, "Add at least one medicine.")
        else:
            with transaction.atomic():
                rx = form.save(commit=False)
                rx.encounter = enc
                rx.doctor = enc.doctor if request.user.role == ADMIN else request.user
                rx.save()
                for f in filled:
                    item = f.save(commit=False)
                    item.prescription = rx
                    item.save()
            messages.success(request, "Prescription saved.")
            return redirect("prescription_detail", pk=rx.pk)
    return render(
        request, "clinical/prescription_form.html", {"form": form, "formset": formset, "enc": enc}
    )


@login_required
def prescription_detail(request, pk):
    rx = get_object_or_404(
        Prescription.objects.select_related("encounter__patient", "doctor__doctor_profile").prefetch_related(
            "items"
        ),
        pk=pk,
        encounter__in=encounters_for(request.user),
    )
    return render(request, "clinical/prescription_print.html", {"rx": rx, "enc": rx.encounter})


@role_required(ADMIN, DOCTOR, RECEPTION)
def encounter_close(request, pk):
    enc = get_object_or_404(encounters_for(request.user), pk=pk)
    if not enc.is_active:
        messages.info(request, "Already closed.")
        return redirect("encounter_detail", pk=pk)
    form = DischargeForm(request.POST or None, instance=enc)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            enc = form.save(commit=False)
            enc.close(form.cleaned_data["discharge_summary"])
        messages.success(
            request, "Patient discharged." if enc.visit_type == "IPD" else "Visit completed."
        )
        return redirect("encounter_detail", pk=pk)
    title = "Discharge patient" if enc.visit_type == "IPD" else "Complete visit"
    return render(
        request,
        "form.html",
        {"form": form, "title": f"{title} - {enc.ref_no}", "submit": "Confirm", "cancel_url": f"/clinical/{pk}/"},
    )
