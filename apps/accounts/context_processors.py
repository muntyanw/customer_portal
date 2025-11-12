# apps/accounts/context_processors.py
from .roles import is_manager, is_customer

def roles(request):
    user = getattr(request, "user", None)
    return {
        "is_manager": is_manager(user) if user else False,
        "is_customer": is_customer(user) if user else False,
    }
