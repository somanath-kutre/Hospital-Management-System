from django.urls import path

from . import views

urlpatterns = [
    path("", views.encounter_list, name="encounter_list"),
    path("new/", views.encounter_create, name="encounter_create"),
    path("<int:pk>/", views.encounter_detail, name="encounter_detail"),
    path("<int:pk>/edit/", views.encounter_edit, name="encounter_edit"),
    path("<int:pk>/treatment/", views.treatment_add, name="treatment_add"),
    path("<int:pk>/prescribe/", views.prescription_add, name="prescription_add"),
    path("<int:pk>/close/", views.encounter_close, name="encounter_close"),
    path("prescriptions/<int:pk>/", views.prescription_detail, name="prescription_detail"),
]
