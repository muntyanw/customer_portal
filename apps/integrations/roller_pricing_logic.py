# -*- coding: utf-8 -*-
"""
UA: Бізнес-логіка розрахунку цін для всіх систем (усі вкладки прайсу):
    - визначення типу системи за назвою листа/секції
    - конвертація введеної ширини в "розрахункову" ширину для прайсу
    - прев'ю ціни для конкретної секції/тканини.

EN: Business logic for roller systems (all sheets):
    - detect system type from sheet / section titles
    - convert user width (fabric / gabarit / bead) to price width
    - compute price preview for a given sheet/section/fabric.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

from .google_sheets import (
    parse_sheet_price_section,
    pick_width_band,
    Q,
    round_money,
)


# ---- 1. Визначення типу системи за назвою листа + секції ----

def _detect_system_type(sheet_name: str, section_title: str) -> str:
    """
    Повертає умовний код системи. Працює за "contains" по тексту.
    Якщо система не впізнана, повертає 'generic'.
    """
    text = f"{sheet_name} {section_title}".lower()

    # Фальш-ролети (твоя перша вкладка)
    if "фальш" in text:
        return "falshi"

    # Міні Besta, відкрита, 19-й вал (і день-ніч ті самі правила)
    if "міні" in text and "besta" in text and "19" in text:
        return "mini_besta_19"

    # Uni Besta з плоскими напрямними
    if "uni" in text and "besta" in text and "плос" in text:
        return "uni_besta_flat"

    # Uni Besta з П-образними напрямними
    if "uni" in text and "besta" in text and "п-образ" in text:
        return "uni_besta_p"

    # Відкрита Besta, 25-й вал
    if "відкрита" in text and "25" in text and "besta" in text and "день" not in text:
        return "open_besta_25"

    # Відкрита 25-й вал, день-ніч
    if "відкрита" in text and "25" in text and ("день-ніч" in text or "день-ноч" in text):
        return "open_25_daynight"

    # Відкрита Louvolite, 32-й вал
    if "louvolite" in text or "louvolit" in text:
        return "open_louvolite_32"

    # Відкрита пружинна
    if "пружин" in text and "відкрита" in text:
        return "spring_open"

    # Закрита пружинна з П-образними напрямними
    if "пружин" in text and "закрита" in text and "п-образ" in text:
        return "spring_closed_p"

    # Відкрита, 47-й вал
    if "47" in text and "відкрита" in text:
        return "open_47"

    # Якщо нічого не впізнали — залишаємо "generic"
    return "generic"


# ---- 2. Конвертація ширини за правилами системи ----

def _convert_width_for_system(
    sheet_name: str,
    section_title: str,
    input_width_mm: int,
    gabarit_width_flag: bool,
) -> int:
    """
    UA:
      - input_width_mm: те, що користувач ввів у полі "Ширина, мм".
      - gabarit_width_flag:
            False -> ввели "ширину за замовчуванням" (як в описі системи),
            True  -> ввели "альтернативний варіант" (габарит або тканина, залежно від системи).

      Повертає width_for_price_mm — ту ширину, яка повинна потрапити в прайс
      (у колонку 'Ширина готового виробу ...').

    Логіка відповідно до твого опису (коментарі всередині).
    """
    sys_type = _detect_system_type(sheet_name, section_title)
    w = int(input_width_mm)

    # --- Фальш-ролети ---
    # У тебе раніше: "Габаритна ширина (+4мм)" — тобто
    #   габарит = по тканині + 4мм
    # Вважаємо, що прайс побудований по габариту.
    if sys_type == "falshi":
        if gabarit_width_flag:
            # користувач ввів габарит
            return max(w, 0)
        else:
            # користувач ввів по тканині -> габарит = тканина + 4
            return max(w + 4, 0)

    # --- Мінi Besta, відкрита, 19-й вал (і день-ніч) ---
    # В описі:
    #   По умолчанию ширина по ткани.
    #   Габаритная ширина -35мм = размер по ткани.
    # → габарит = тканина + 35мм; прайс по габариту.
    if sys_type == "mini_besta_19":
        if gabarit_width_flag:
            # ввели габарит
            return max(w, 0)
        else:
            # ввели тканину -> габарит
            return max(w + 35, 0)

    # --- Uni Besta з плоскими напрямними ---
    #   По умолчанию ширина по внешним краям штапика.
    #   Если размер сняли по ткани, +44мм = по внешним краям штапика.
    # Для простоти трактуємо gabarit_width_flag як "розмір по тканині".
    if sys_type == "uni_besta_flat":
        if gabarit_width_flag:
            # ввели по тканині -> конвертуємо в по штапику
            return max(w + 44, 0)
        else:
            # ввели по штапику = вже те, що треба для прайсу
            return max(w, 0)

    # --- Uni Besta з П-образними напрямними ---
    #   По умолчанию ширина по внешним краям штапика.
    #   Если размер габаритный, -20мм = по внешним краям штапика.
    # Тут gabarit_width_flag природньо = "ввели габарит".
    if sys_type == "uni_besta_p":
        if gabarit_width_flag:
            # ввели габарит -> перерахувати в по штапику
            return max(w - 20, 0)
        else:
            # ввели по штапику
            return max(w, 0)

    # --- Відкрита Besta, 25-й вал ---
    #   По умолчанию ширина по ткани.
    #   Габаритная ширина -35мм = размер по ткани.
    # → габарит = тканина + 35, прайс по габариту.
    if sys_type == "open_besta_25":
        if gabarit_width_flag:
            return max(w, 0)       # ввели габарит
        else:
            return max(w + 35, 0)  # ввели тканину

    # --- Відкрита, 25-й вал, день-ніч ---
    #   По умолчанию по ткани.
    #   Габаритная ширина -30мм = размер по ткани. → габарит = тканина + 30.
    if sys_type == "open_25_daynight":
        if gabarit_width_flag:
            return max(w, 0)
        else:
            return max(w + 30, 0)

    # --- Відкрита Louvolite, 32-й вал ---
    #   По умолчанию по ткани.
    #   Габаритная ширина -42мм = размер по ткани. → габарит = тканина + 42.
    if sys_type == "open_louvolite_32":
        if gabarit_width_flag:
            return max(w, 0)
        else:
            return max(w + 42, 0)

    # --- Відкрита пружинна система ---
    #   По умолчанию по ткани.
    #   Габаритная ширина -35мм = размер по ткани. → габарит = тканина + 35.
    if sys_type == "spring_open":
        if gabarit_width_flag:
            return max(w, 0)
        else:
            return max(w + 35, 0)

    # --- Закрита пружинна з П-образними напрямними ---
    #   Варианты: по внешним краям штапика и габарит.
    #   По умолчанию по внешним краям штапика.
    #   Если размер габаритный, -20мм = по внешним краям штапика.
    if sys_type == "spring_closed_p":
        if gabarit_width_flag:
            return max(w - 20, 0)  # ввели габарит
        else:
            return max(w, 0)       # по штапику

    # --- Відкрита, 47-й вал ---
    #   По умолчанию по ткани.
    #   Габаритная ширина -50мм = размер по ткани. → габарит = тканина + 50.
    if sys_type == "open_47":
        if gabarit_width_flag:
            return max(w, 0)
        else:
            return max(w + 50, 0)

    # --- За замовчуванням: нічого не знаємо, беремо як є ---
    return max(w, 0)


# ---- 3. Прев'ю ціни для будь-якої секції (всі вкладки) ----

def preview_section_price(
    google_sheet_url: str,
    sheet_name: str,
    section_title: str,
    fabric_name: str,
    width_mm: int,
    gabarit_height_mm: int,
    gabarit_width_flag: bool,
    magnets: bool,
    *,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    UA: Розраховує прев'ю ціни:
      - парсить потрібну секцію на вказаному листі
      - конвертує введену ширину в "ширину для прайсу" за правилами системи
      - знаходить смугу ширини, ціну бази, доплату за висоту, магніти
      - повертає структуру, сумісну з попереднім preview_first + fabric_params.

    EN: Price preview for given sheet/section/fabric.
    """
    # 1) Спочатку парсимо секцію (ширини + тканини + магніти)
    parsed = parse_sheet_price_section(
        google_sheet_url=google_sheet_url,
        sheet_name=sheet_name,
        section_title=section_title,
        force_refresh=force_refresh,
    )

    # 2) Конвертація ширини за правилами системи
    price_width_mm = _convert_width_for_system(
        sheet_name=sheet_name,
        section_title=section_title,
        input_width_mm=width_mm,
        gabarit_width_flag=gabarit_width_flag,
    )

    width_bands = parsed["width_bands"]
    idx = pick_width_band(width_bands, price_width_mm)
    if idx is None:
        raise ValueError("Ширина поза діапазонами прайсу")

    # 3) Знаходимо тканину
    fabric = next(
        (f for f in parsed["fabrics"] if f["name"].lower() == fabric_name.lower()),
        None,
    )
    if not fabric:
        raise ValueError("Тканину не знайдено")

    base_cell = fabric["prices_by_band"][idx]
    if base_cell is None:
        raise ValueError("Ціна відсутня у вибраній смузі")

    base = Q(base_cell)

    # 4) Доплата за висоту (та ж логіка, що й у price_preview_first)
    limit = fabric["gabarit_limit_mm"] or 0
    if gabarit_height_mm <= limit:
        surcharge = Q("0.00")
    else:
        over = gabarit_height_mm - limit
        steps = (over + 99) // 100  # кожні 100мм (10см), округлення вгору
        surcharge = round_money(base * Q("0.10") * Q(int(steps)))

    magnets_price = Q(parsed["magnets_price_eur"]) if magnets else Q("0.00")
    subtotal = round_money(base + surcharge + magnets_price)

    fabric_params = {
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": fabric["gabarit_limit_mm"],
    }

    return {
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": limit,
        "band_index": idx,
        "band_label": width_bands[idx],
        "base_price_eur": str(round_money(base)),
        "surcharge_height_eur": str(surcharge),
        "magnets_price_eur": str(round_money(magnets_price)),
        "subtotal_eur": str(subtotal),
        "fabric_params": fabric_params,
        # технічна інфа — раптом знадобиться для дебагу:
        "price_width_mm": price_width_mm,
        "input_width_mm": width_mm,
        "system_type": _detect_system_type(sheet_name, section_title),
    }
