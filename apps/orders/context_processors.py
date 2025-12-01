# apps/orders/context_processors.py
from decimal import Decimal
from .services_currency import get_current_eur_rate


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
