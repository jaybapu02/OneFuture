"""Role-based access control helpers.

Roles:
* Admin  -> user.is_staff  (can access Django admin + management pages)
* Trainer -> authenticated user with a TrainerProfile (never staff)
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from trainers.models import TrainerProfile


def get_trainer_profile(user):
    """Return the TrainerProfile for a user, or None."""
    if user is None or not user.is_authenticated:
        return None
    return getattr(user, "profile", None)


def staff_required(view_func):
    """Allow only staff (admin) users."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def trainer_required(view_func):
    """Allow only authenticated users who have a TrainerProfile."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if get_trainer_profile(request.user) is None:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped
