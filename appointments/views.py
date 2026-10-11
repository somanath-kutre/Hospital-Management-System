from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import ADMIN, DOCTOR, PATIENT, RECEPTION, role_required

from .forms import AppointmentForm
from .models import Appointment


def scoped_appointments(user):
    qs = Appointment.objects.select_related("patient", "doctor")
    if user.is_superuser or user.role in (ADMIN, RECEPTION):
        return qs
    if user.role == DOCTOR:
        return qs.filter(doctor=user)
    return qs.filter(patient__user=user)


@login_required
def appointment_list(request):
    today = timezone.localdate()
    when = request.GET.get("when", "upcoming")
    status = request.GET.get("status", "")
    qs = scoped_appointments(request.user)
    if when == "today":
        qs = qs.filter(date=today)
    elif when == "past":
        qs = qs.filter(date__lt=today).order_by("-date", "-time")
    elif when == "upcoming":
        qs = qs.filter(date__gte=today)
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        "appointments/list.html",
        {
            "appointments": qs,
            "when": when,
            "status": status,
            "statuses": Appointment.Status.choices,
        },
    )


@role_required(ADMIN, RECEPTION, PATIENT)
def appointment_create(request):
    user = request.user
    own_patient = getattr(user, "patient", None)
    if user.role == PATIENT and own_patient is None:
        messages.error(request, "No patient record is linked to your account. Contact the front desk.")
        return redirect("dashboard")

    form = AppointmentForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        if user.role == PATIENT:
            appt.patient = own_patient
        appt.created_by = user
        appt.save()
        messages.success(request, "Appointment booked.")
        return redirect("appointment_list")
    return render(
        request,
        "form.html",
        {"form": form, "title": "Book appointment", "cancel_url": "/appointments/"},
    )


@login_required
@require_POST
def appointment_status(request, pk, new_status):
    user = request.user
    appt = get_object_or_404(scoped_appointments(user), pk=pk)
    allowed = {s for s, _ in Appointment.Status.choices} - {Appointment.Status.SCHEDULED}
    if new_status not in allowed:
        raise PermissionDenied
    if user.role == PATIENT and new_status != Appointment.Status.CANCELLED:
        raise PermissionDenied
    if appt.status != Appointment.Status.SCHEDULED:
        messages.error(request, "Only scheduled appointments can be changed.")
    else:
        appt.status = new_status
        appt.save(update_fields=["status"])
        messages.success(request, f"Appointment marked {appt.get_status_display().lower()}.")
    return redirect("appointment_list")


@role_required(ADMIN, RECEPTION, DOCTOR)
@require_POST
def appointment_consult(request, pk):
    """Turn a scheduled appointment into an OPD encounter."""
    from clinical.models import Encounter

    appt = get_object_or_404(scoped_appointments(request.user), pk=pk)
    existing = Encounter.objects.filter(appointment=appt).first()
    if existing:
        return redirect("encounter_detail", pk=existing.pk)
    if appt.status != Appointment.Status.SCHEDULED:
        messages.error(request, "Only scheduled appointments can start a consultation.")
        return redirect("appointment_list")
    enc = Encounter.objects.create(
        patient=appt.patient,
        doctor=appt.doctor,
        visit_type=Encounter.Type.OPD,
        appointment=appt,
        chief_complaint=appt.reason,
    )
    appt.status = Appointment.Status.COMPLETED
    appt.save(update_fields=["status"])
    messages.success(request, "OPD visit started.")
    return redirect("encounter_detail", pk=enc.pk)
