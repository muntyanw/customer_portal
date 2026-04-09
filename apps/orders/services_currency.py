# apps/orders/services_currency.py
from decimal import Decimal

import requests
from django.utils import timezone

from .models import CurrencyRate


SUPPORTED_CURRENCIES = ("EUR", "USD")


def get_current_currency_rate(currency: str) -> Decimal:
    currency = (currency or "").upper()
    if currency not in SUPPORTED_CURRENCIES:
        return Decimal("0")
    obj = CurrencyRate.objects.filter(currency=currency).order_by("-updated_at").first()
    if obj:
        return obj.rate_uah
    return Decimal("0")


def get_current_eur_rate() -> Decimal:
    return get_current_currency_rate("EUR")


def get_current_usd_rate() -> Decimal:
    return get_current_currency_rate("USD")


def update_currency_rate_from_privatbank(currency: str, timeout: int = 10) -> CurrencyRate:
    currency = (currency or "").upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise RuntimeError(f"Unsupported currency: {currency}")

    url = "https://api.privatbank.ua/p24api/pubinfo"
    params = {"json": "", "exchange": "", "coursid": "5"}

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError("PrivatBank response is empty")

    row = next((row for row in data if str(row.get("ccy")).upper() == currency), None)
    if not row:
        raise RuntimeError(f"{currency} rate not found in PrivatBank response")

    sale_rate = Decimal(str(row.get("sale")))
    obj, _ = CurrencyRate.objects.update_or_create(
        currency=currency,
        defaults={
            "rate_uah": sale_rate,
            "source": "PrivatBank sale",
            "updated_at": timezone.now(),
        },
    )
    return obj


def update_eur_rate_from_nbu(timeout: int = 10) -> CurrencyRate:
    return update_currency_rate_from_privatbank("EUR", timeout=timeout)


def update_usd_rate_from_nbu(timeout: int = 10) -> CurrencyRate:
    return update_currency_rate_from_privatbank("USD", timeout=timeout)
