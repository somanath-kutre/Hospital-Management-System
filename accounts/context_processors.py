def roles(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    role = user.role
    return {
        "is_admin": role == "admin",
        "is_doctor": role == "doctor",
        "is_reception": role == "reception",
        "is_patient": role == "patient",
        "is_staff_role": role in ("admin", "doctor", "reception"),
        "is_front_desk": role in ("admin", "reception"),
    }
