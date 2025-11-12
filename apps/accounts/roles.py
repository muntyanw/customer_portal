# apps/accounts/roles.py
from django.contrib.auth import get_user_model
User = get_user_model()

def is_manager(user: User) -> bool:
    # Manager = внутрішня роль менеджера порталу
    return bool(user and user.is_authenticated and getattr(user, "is_manager", False))

def is_customer(user: User) -> bool:
    # Customer = стандартний клієнт (за замовчуванням True у нашій моделі)
    return bool(user and user.is_authenticated and getattr(user, "is_customer", False))
