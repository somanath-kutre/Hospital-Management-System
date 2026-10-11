from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/add/", views.staff_add, name="staff_add"),
    path("staff/<int:pk>/toggle/", views.staff_toggle, name="staff_toggle"),
]
