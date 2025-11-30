# apps/orders/utils_components.py (или внизу views.py)

from decimal import Decimal, InvalidOperation
import re
from typing import List, Dict, Any
from django.http import QueryDict


def parse_components_from_post(post: QueryDict) -> List[Dict[str, Any]]:
    """
    EN: Parse components[*][field] rows from POST data and normalize values.
    UA: Парсить рядки components[*][field] з POST та нормалізувати значення.
    """
    pattern = re.compile(r"^components\[(\d+)\]\[(\w+)\]$")
    tmp: Dict[str, Dict[str, str]] = {}

    for full_key, value in post.items():
        m = pattern.match(full_key)
        if not m:
            continue
        idx, field = m.groups()
        tmp.setdefault(idx, {})[field] = (value or "").strip()

    result: List[Dict[str, Any]] = []

    for idx in sorted(tmp.keys(), key=int):
        row = tmp[idx]
        name = row.get("name", "").strip()
        if not name:
            # EN: skip rows without name
            # UA: пропускаємо рядки без найменування
            continue

        qty_str = (row.get("quantity") or "").strip() or "0"
        try:
            qty = Decimal(qty_str.replace(",", "."))
        except InvalidOperation:
            qty = Decimal("0")

        if qty <= 0:
            # EN: skip non-positive quantity
            # UA: пропускаємо нульову/від'ємну кількість
            continue

        price_str = (row.get("price_eur") or "").strip()
        price_str = price_str.replace(" ", "").replace(",", ".")
        try:
            price = Decimal(price_str)
        except InvalidOperation:
            price = Decimal("0")

        unit = (row.get("unit") or "").strip()
        color = (row.get("color") or "").strip()

        result.append(
            {
                "name": name,
                "color": color,
                "unit": unit,
                "price_eur": price,
                "quantity": qty,
            }
        )

    return result
