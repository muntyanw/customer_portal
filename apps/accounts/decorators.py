# apps/accounts/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .roles import is_manager

def manager_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not is_manager(request.user):
            raise PermissionDenied("Manager role required")
        return view_func(request, *args, **kwargs)
    return _wrapped
