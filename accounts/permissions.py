from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMIN = "admin"
DOCTOR = "doctor"
RECEPTION = "reception"
PATIENT = "patient"

STAFF = (ADMIN, DOCTOR, RECEPTION)
FRONT_DESK = (ADMIN, RECEPTION)


def role_required(*roles):
    """Allow only the given roles (superusers always pass). Anonymous -> login page."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.role in roles:
                return view(request, *args, **kwargs)
            raise PermissionDenied

        return login_required(wrapper)

    return decorator
