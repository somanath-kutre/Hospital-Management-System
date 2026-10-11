from django.urls import path

from . import views

urlpatterns = [
    path("", views.invoice_list, name="invoice_list"),
    path("new/", views.invoice_new, name="invoice_new"),
    path("from-encounter/<int:encounter_pk>/", views.invoice_from_encounter, name="invoice_from_encounter"),
    path("<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("<int:pk>/add-item/", views.invoice_add_item, name="invoice_add_item"),
    path("<int:pk>/add-payment/", views.invoice_add_payment, name="invoice_add_payment"),
]
