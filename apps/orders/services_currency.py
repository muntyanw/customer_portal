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
    EN: Fetch EUR rate from NBU API and save to DB.
    UA: Отримує курс EUR з API НБУ та зберігає в БД.
    """
    # Офіційне API НБУ для курсу EUR у форматі JSON
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"
    params = {"valcode": "EUR", "json": 1}

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise RuntimeError("NBU response is empty")

    rate = Decimal(str(data[0]["rate"]))

    obj, _ = CurrencyRate.objects.update_or_create(
        currency="EUR",
        defaults={
            "rate_uah": rate,
            "source": "NBU",
            "updated_at": timezone.now(),
        },
    )
    return obj
