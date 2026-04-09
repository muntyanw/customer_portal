# apps/orders/context_processors.py
from decimal import Decimal
from .services_currency import get_current_eur_rate, get_current_usd_rate
from .models import CurrencyRate
from .views import compute_balance


def currency_rate(request):
    """
    EN: Add current EUR/UAH rate to template context.
    UA: Додає поточний курс EUR/UAH до контексту шаблонів.
    """
    try:
        eur_rate = get_current_eur_rate()
    except Exception:
        eur_rate = Decimal("0")
    try:
        usd_rate = get_current_usd_rate()
    except Exception:
        usd_rate = Decimal("0")

    eur_rate_obj = (
        CurrencyRate.objects.filter(currency="EUR")
        .order_by("-updated_at")
        .only("updated_at")
        .first()
    )
    usd_rate_obj = (
        CurrencyRate.objects.filter(currency="USD")
        .order_by("-updated_at")
        .only("updated_at")
        .first()
    )

    return {
        "eur_rate": eur_rate,
        "usd_rate": usd_rate,
        "eur_rate_updated_at": eur_rate_obj.updated_at if eur_rate_obj else None,
        "usd_rate_updated_at": usd_rate_obj.updated_at if usd_rate_obj else None,
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
