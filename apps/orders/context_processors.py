# apps/orders/context_processors.py
from decimal import Decimal
from .services_currency import get_current_eur_rate
from .views import compute_balance


def currency_rate(request):
    """
    EN: Add current EUR/UAH rate to template context.
    UA: Додає поточний курс EUR/UAH до контексту шаблонів.
    """
    try:
        rate = get_current_eur_rate()
    except Exception:
        rate = Decimal("0")

    return {
        "eur_rate": rate,
    }


def user_balance(request):
    """
    EN: Add current balance for authenticated user to context.
    UA: Додає поточний баланс користувача у контекст.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"user_balance": None}
    try:
        bal = compute_balance(request.user)
    except Exception:
        bal = None
    return {"user_balance": bal}
