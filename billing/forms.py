from django import forms

from accounts.forms import BootstrapModelForm
from patients.models import Patient

from .models import Invoice, InvoiceItem, Payment


class NewInvoiceForm(BootstrapModelForm):
    class Meta:
        model = Invoice
        fields = ["patient", "notes"]


class InvoiceEditForm(BootstrapModelForm):
    class Meta:
        model = Invoice
        fields = ["discount", "notes"]

    def clean_discount(self):
        d = self.cleaned_data["discount"]
        if d < 0:
            raise forms.ValidationError("Discount cannot be negative.")
        if d > self.instance.subtotal:
            raise forms.ValidationError("Discount cannot exceed the invoice subtotal.")
        return d


class ItemForm(BootstrapModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["description", "quantity", "unit_price"]

    def clean_unit_price(self):
        p = self.cleaned_data["unit_price"]
        if p < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return p

    def clean_quantity(self):
        q = self.cleaned_data["quantity"]
        if q < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return q


class PaymentForm(BootstrapModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "reference", "paid_on"]
        widgets = {"paid_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        if self.invoice is not None and amount > self.invoice.balance:
            raise forms.ValidationError(f"Amount exceeds the balance due ({self.invoice.balance}).")
        return amount
