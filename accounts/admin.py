from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DoctorProfile, User


class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    extra = 0
    max_num = 1


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Hospital", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Hospital", {"fields": ("role", "phone")}),)
    list_display = ("username", "display_name", "role", "phone", "is_active")
    list_filter = ("role", "is_active")
    inlines = [DoctorProfileInline]
