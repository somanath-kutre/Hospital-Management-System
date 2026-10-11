from django.urls import path

from . import views

urlpatterns = [
    path("", views.appointment_list, name="appointment_list"),
    path("book/", views.appointment_create, name="appointment_create"),
    path("<int:pk>/status/<str:new_status>/", views.appointment_status, name="appointment_status"),
    path("<int:pk>/consult/", views.appointment_consult, name="appointment_consult"),
]
