from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string

from accounts.models import User
from accounts.permissions import ADMIN, DOCTOR, FRONT_DESK, PATIENT, RECEPTION, STAFF, role_required

from .forms import PatientForm
from .models import Patient


@role_required(*STAFF)
def patient_list(request):
    q = request.GET.get("q", "").strip()
    qs = Patient.objects.all()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(code__icontains=q)
            | Q(phone__icontains=q)
        )
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "patients/list.html", {"page": page, "q": q})


@role_required(*FRONT_DESK)
def patient_add(request):
    form = PatientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        patient = form.save()
        if form.cleaned_data.get("create_login"):
            password = get_random_string(10)
            user = User.objects.create_user(
                username=patient.code.lower(),
                password=password,
                first_name=patient.first_name,
                last_name=patient.last_name,
                email=patient.email,
                phone=patient.phone,
                role=User.Role.PATIENT,
            )
            patient.user = user
            patient.save(update_fields=["user"])
            messages.warning(
                request,
                f"Portal login created -> username: {user.username} | temporary password: {password} "
                "(shown only once, please hand it to the patient).",
            )
        messages.success(request, f"Patient {patient.full_name} registered ({patient.code}).")
        return redirect("patient_detail", pk=patient.pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": "Register new patient", "cancel_url": "/patients/"},
    )


@role_required(*FRONT_DESK)
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient, creating=False)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Patient details updated.")
        return redirect("patient_detail", pk=patient.pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": f"Edit {patient.full_name}", "cancel_url": f"/patients/{pk}/"},
    )


@login_required
def my_profile(request):
    patient = getattr(request.user, "patient", None)
    if not patient:
        raise PermissionDenied
    return redirect("patient_detail", pk=patient.pk)


@login_required
def patient_detail(request, pk):
    from clinical.views import encounters_for

    user = request.user
    patient = get_object_or_404(Patient, pk=pk)
    if user.role == PATIENT and patient.user_id != user.id:
        raise PermissionDenied

    can_billing = user.role in (ADMIN, RECEPTION) or user.role == PATIENT
    ctx = {
        "patient": patient,
        "encounters": encounters_for(user).filter(patient=patient),
        "can_billing": can_billing,
    }
    appts = patient.appointments.select_related("doctor")
    if user.role == DOCTOR:
        appts = appts.filter(doctor=user)
    ctx["appointments"] = appts[:10]
    if can_billing:
        ctx["invoices"] = patient.invoices.prefetch_related("items", "payments")
    return render(request, "patients/detail.html", ctx)
