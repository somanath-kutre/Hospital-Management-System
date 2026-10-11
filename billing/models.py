from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="invoices")
    encounter = models.ForeignKey(
        "clinical.Encounter", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    discount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"INV{self.pk:06d}"
            super().save(update_fields=["number"])

    # Totals use .all() so prefetch_related("items", "payments") avoids extra queries.
    @property
    def subtotal(self):
        return sum((i.amount for i in self.items.all()), Decimal("0"))

    @property
    def total(self):
        return max(self.subtotal - self.discount, Decimal("0"))

    @property
    def paid(self):
        return sum((p.amount for p in self.payments.all()), Decimal("0"))

    @property
    def balance(self):
        return self.total - self.paid

    @property
    def status(self):
        if self.total > 0 and self.balance <= 0:
            return "Paid"
        if self.paid > 0:
            return "Partial"
        return "Unpaid"

    def __str__(self):
        return f"{self.number} - {self.patient.full_name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)

    @property
    def amount(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        INSURANCE = "insurance", "Insurance"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    reference = models.CharField(max_length=80, blank=True, help_text="Txn / receipt no.")
    paid_on = models.DateField(default=timezone.localdate)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["paid_on", "id"]

    def __str__(self):
        return f"{self.amount} on {self.paid_on}"
