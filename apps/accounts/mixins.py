# apps/accounts/mixins.py
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from .roles import is_manager

class ManagerRequiredMixin(LoginRequiredMixin):
    """CBV mixin: allow only managers (superuser passes as well via is_staff)."""
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and (is_manager(user) or user.is_staff or user.is_superuser)):
            raise PermissionDenied("Manager role required")
        return super().dispatch(request, *args, **kwargs)
