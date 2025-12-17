# apps/orders/services_currency.py
from decimal import Decimal
from typing import Optional

import requests
from django.utils import timezone

from .models import CurrencyRate


def get_current_eur_rate() -> Decimal:
    """
    EN: Return latest stored EUR/UAH rate.
    UA: Повертає останній збережений курс EUR/UAH.
    """
    obj = (
        CurrencyRate.objects.filter(currency="EUR")
        .order_by("-updated_at")
        .first()
    )
    if obj:
        return obj.rate_uah
    return Decimal("0")


def update_eur_rate_from_nbu(timeout: int = 10) -> CurrencyRate:
    """
    EN: Fetch EUR sale rate from PrivatBank public API and save to DB.
    UA: Отримує курс продажу EUR з публічного API Приватбанку та зберігає в БД.
    """
    url = "https://api.privatbank.ua/p24api/pubinfo"
    params = {"json": "", "exchange": "", "coursid": "5"}

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise RuntimeError("PrivatBank response is empty")

    eur_row = next((row for row in data if str(row.get("ccy")).upper() == "EUR"), None)
    if not eur_row:
        raise RuntimeError("EUR rate not found in PrivatBank response")

    sale_rate = Decimal(str(eur_row.get("sale")))

    obj, _ = CurrencyRate.objects.update_or_create(
        currency="EUR",
        defaults={
            "rate_uah": sale_rate,
            "source": "PrivatBank sale",
            "updated_at": timezone.now(),
        },
    )
    return obj
