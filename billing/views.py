from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import ADMIN, FRONT_DESK, PATIENT, RECEPTION, role_required
from clinical.models import Encounter

from .forms import InvoiceEditForm, ItemForm, NewInvoiceForm, PaymentForm
from .models import Invoice, InvoiceItem


def invoices_for(user):
    qs = Invoice.objects.select_related("patient", "encounter").prefetch_related("items", "payments")
    if user.is_superuser or user.role in (ADMIN, RECEPTION):
        return qs
    if user.role == PATIENT:
        return qs.filter(patient__user=user)
    raise PermissionDenied  # doctors have no billing access


def generate_invoice(encounter, user):
    """Build an invoice from the consultation fee, bed stay and billable treatments."""
    invoice = Invoice.objects.create(
        patient=encounter.patient, encounter=encounter, created_by=user, notes=f"Visit {encounter.ref_no}"
    )
    profile = getattr(encounter.doctor, "doctor_profile", None)
    if profile and profile.consultation_fee > 0:
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f"Consultation - {encounter.doctor.doctor_label}",
            quantity=1,
            unit_price=profile.consultation_fee,
        )
    if encounter.visit_type == Encounter.Type.IPD and encounter.bed and encounter.bed.daily_charge > 0:
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f"Bed charges - {encounter.bed} ({encounter.stay_days} day(s))",
            quantity=encounter.stay_days,
            unit_price=encounter.bed.daily_charge,
        )
    for t in encounter.treatments.all():
        if t.charge > 0:
            InvoiceItem.objects.create(
                invoice=invoice, description=t.title, quantity=1, unit_price=t.charge
            )
    return invoice


@login_required
def invoice_list(request):
    qs = invoices_for(request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__code__icontains=q)
        )
    invoices = list(qs[:200])
    status = request.GET.get("status", "")
    if status in ("Paid", "Partial", "Unpaid"):
        invoices = [i for i in invoices if i.status == status]
    return render(request, "billing/invoice_list.html", {"invoices": invoices, "q": q, "status": status})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(invoices_for(request.user), pk=pk)
    ctx = {"invoice": invoice}
    if request.user.is_superuser or request.user.role in FRONT_DESK:
        ctx["item_form"] = ItemForm()
        ctx["payment_form"] = PaymentForm(invoice=invoice, initial={"amount": invoice.balance})
        ctx["can_manage"] = True
    return render(request, "billing/invoice_detail.html", ctx)


@role_required(*FRONT_DESK)
def invoice_new(request):
    form = NewInvoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        inv = form.save(commit=False)
        inv.created_by = request.user
        inv.save()
        messages.success(request, f"Invoice {inv.number} created. Add line items below.")
        return redirect("invoice_detail", pk=inv.pk)
    return render(request, "form.html", {"form": form, "title": "New invoice", "cancel_url": "/billing/"})


@role_required(*FRONT_DESK)
@require_POST
def invoice_from_encounter(request, encounter_pk):
    enc = get_object_or_404(Encounter, pk=encounter_pk)
    existing = enc.invoices.first()
    if existing:
        messages.info(request, "An invoice already exists for this visit.")
        return redirect("invoice_detail", pk=existing.pk)
    with transaction.atomic():
        invoice = generate_invoice(enc, request.user)
    messages.success(request, f"Invoice {invoice.number} generated.")
    return redirect("invoice_detail", pk=invoice.pk)


@role_required(*FRONT_DESK)
def invoice_edit(request, pk):
    invoice = get_object_or_404(invoices_for(request.user), pk=pk)
    form = InvoiceEditForm(request.POST or None, instance=invoice)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Invoice updated.")
        return redirect("invoice_detail", pk=pk)
    return render(
        request,
        "form.html",
        {"form": form, "title": f"Discount / notes - {invoice.number}", "cancel_url": f"/billing/{pk}/"},
    )


@role_required(*FRONT_DESK)
@require_POST
def invoice_add_item(request, pk):
    invoice = get_object_or_404(invoices_for(request.user), pk=pk)
    form = ItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.invoice = invoice
        item.save()
        messages.success(request, "Item added.")
    else:
        messages.error(request, "Could not add item: " + "; ".join(sum(form.errors.values(), [])))
    return redirect("invoice_detail", pk=pk)


@role_required(*FRONT_DESK)
@require_POST
def invoice_add_payment(request, pk):
    invoice = get_object_or_404(invoices_for(request.user), pk=pk)
    form = PaymentForm(request.POST, invoice=invoice)
    if form.is_valid():
        pay = form.save(commit=False)
        pay.invoice = invoice
        pay.received_by = request.user
        pay.save()
        messages.success(request, "Payment recorded.")
    else:
        messages.error(request, "Could not record payment: " + "; ".join(sum(form.errors.values(), [])))
    return redirect("invoice_detail", pk=pk)
