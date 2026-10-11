from django.contrib import admin

from .models import Invoice, InvoiceItem, Payment


class ItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "patient", "total", "paid", "balance", "status", "created_at")
    search_fields = ("number", "patient__first_name", "patient__last_name", "patient__code")
    inlines = [ItemInline, PaymentInline]
