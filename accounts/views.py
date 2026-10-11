from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PatientSignupForm, StaffCreateForm
from .models import User
from .permissions import ADMIN, DOCTOR, PATIENT, RECEPTION, role_required


@login_required
def dashboard(request):
    from appointments.models import Appointment
    from billing.models import Invoice, Payment
    from clinical.models import Encounter
    from patients.models import Patient

    user = request.user
    today = timezone.localdate()
    ctx = {}

    if user.role in (ADMIN, RECEPTION):
        ctx["mode"] = "front"
        ctx["patient_count"] = Patient.objects.count()
        ctx["todays_appointments"] = Appointment.objects.filter(date=today).select_related(
            "patient", "doctor"
        )
        ctx["ipd_active"] = Encounter.objects.filter(
            visit_type=Encounter.Type.IPD, status=Encounter.Status.ACTIVE
        ).select_related("patient", "doctor", "bed")
        ctx["opd_today"] = Encounter.objects.filter(
            visit_type=Encounter.Type.OPD, admitted_at__date=today
        ).count()
        ctx["revenue_today"] = (
            Payment.objects.filter(paid_on=today).aggregate(s=Sum("amount"))["s"] or 0
        )
        invoices = Invoice.objects.select_related("patient").prefetch_related("items", "payments")
        ctx["pending_invoices"] = [i for i in invoices if i.balance > 0][:10]
    elif user.role == DOCTOR:
        ctx["mode"] = "doctor"
        ctx["todays_appointments"] = Appointment.objects.filter(
            doctor=user, date=today
        ).select_related("patient")
        ctx["ipd_active"] = Encounter.objects.filter(
            doctor=user, visit_type=Encounter.Type.IPD, status=Encounter.Status.ACTIVE
        ).select_related("patient", "bed")
        ctx["open_encounters"] = Encounter.objects.filter(
            doctor=user, status=Encounter.Status.ACTIVE, visit_type=Encounter.Type.OPD
        ).select_related("patient")
    else:
        ctx["mode"] = "patient"
        patient = getattr(user, "patient", None)
        ctx["patient"] = patient
        if patient:
            ctx["upcoming"] = patient.appointments.filter(
                date__gte=today, status="scheduled"
            ).select_related("doctor")
            ctx["recent_encounters"] = patient.encounters.select_related("doctor")[:5]
            invoices = patient.invoices.prefetch_related("items", "payments")
            ctx["due_invoices"] = [i for i in invoices if i.balance > 0]
    return render(request, "dashboard.html", ctx)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = PatientSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your patient account has been created.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@role_required(ADMIN)
def staff_list(request):
    staff = User.objects.exclude(role=PATIENT).select_related("doctor_profile").order_by("role", "username")
    return render(request, "accounts/staff_list.html", {"staff": staff})


@role_required(ADMIN)
def staff_add(request):
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"{user.get_role_display()} '{user.username}' created.")
        return redirect("staff_list")
    return render(
        request,
        "form.html",
        {"form": form, "title": "Add staff member", "cancel_url": "/staff/"},
    )


@role_required(ADMIN)
@require_POST
def staff_toggle(request, pk):
    target = get_object_or_404(User.objects.exclude(role=PATIENT), pk=pk)
    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        messages.success(
            request, f"{target.username} {'activated' if target.is_active else 'deactivated'}."
        )
    return redirect("staff_list")
