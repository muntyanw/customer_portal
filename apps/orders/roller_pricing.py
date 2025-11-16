# apps/orders/roller_pricing.py
# -*- coding: utf-8 -*-
"""
Новая бизнес-логика расчёта:
- Mini Besta (открытая, 19 вал, день-ночь)
- Uni Besta (плоские направляющие / П-образные)
- Пружинные системы
- Открытые 25/32/47 валы
Работает на базе существующих функций google_sheets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, List
from decimal import Decimal
from django.conf import settings

# ⬇ используем ТВОИ функции, НЕ создаём sheets_io.py
from apps.integrations.google_sheets import (
    Q,
    round_money,
    parse_first_sheet_price_section,
    pick_width_band,
)

WidthKind = Literal["fabric", "gabarit", "shtapik"]


# -------------------------------------------------------------------
#  RULE: преобразование введённой ширины в каноническую (по ткани)
# -------------------------------------------------------------------
@dataclass
class WidthRule:
    canonical: WidthKind  # канонический вид («fabric»)
    default_input: WidthKind
    offsets_to_canonical: Dict[WidthKind, int]

    def to_canonical(self, width_mm: int, input_kind: Optional[WidthKind]) -> int:
        use_kind: WidthKind = input_kind or self.default_input
        if use_kind not in self.offsets_to_canonical:
            raise ValueError(f"Вид ширины '{use_kind}' не поддерживается для данной системы")

        return width_mm + int(self.offsets_to_canonical[use_kind])


# -------------------------------------------------------------------
#  Конфиг системы
# -------------------------------------------------------------------
@dataclass
class PriceSystemConfig:
    code: str
    title: str
    section_title: str          # название секции в Google Sheet (как в merged header)
    width_rule: WidthRule       # правило ширины
    height_surcharge_step_mm: int = 100
    height_surcharge_pct: Decimal = field(default_factory=lambda: Q("0.10"))
    magnets_supported: bool = True


# -------------------------------------------------------------------
#  URL прайса (можно вынести в settings)
# -------------------------------------------------------------------
PRICE_SHEET_URL: str = getattr(
    settings,
    "ROLLER_PRICE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1vjwqhZ0-9SWcN-u8Oa-T6ciNmHfMeHU-c2RTv6axqHs/edit"
)


# -------------------------------------------------------------------
#  ВСЕ СИСТЕМЫ (заполнил под твои правила)
# -------------------------------------------------------------------
SYSTEMS: Dict[str, PriceSystemConfig] = {
    # 1) MINI BESTA (ОТКРЫТАЯ, 19 вал, День-ночь)
    "mini_besta_dn_19": PriceSystemConfig(
        code="mini_besta_dn_19",
        title="Відкрита Mini Besta, 19-й вал, день-ніч",
        section_title="Відкрита Mini Besta, день-ніч 19мм",   # ← ТЕКСТ КАК В ПРАЙСЕ
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -35,    # габарит = тканина + 35 → канон = габарит - 35
            },
        ),
    ),

    # 2) UNI BESTA — плоскі напрямні
    "uni_besta_flat": PriceSystemConfig(
        code="uni_besta_flat",
        title="Uni Besta, закрита с-ма, плоскі направляючі",
        section_title="Uni Besta, плоскі направляючі",
        width_rule=WidthRule(
            canonical="shtapik",
            default_input="shtapik",
            offsets_to_canonical={
                "shtapik": 0,
                "fabric": +44,     # тканина + 44 = по штапіку → канон = первично по штапику
            },
        ),
    ),

    # 3) UNI BESTA — П-образні напрямні
    "uni_besta_p": PriceSystemConfig(
        code="uni_besta_p",
        title="Uni Besta, закрита с-ма, П-образні направляючі",
        section_title="Uni Besta, П-подібні направляючі",
        width_rule=WidthRule(
            canonical="shtapik",
            default_input="shtapik",
            offsets_to_canonical={
                "shtapik": 0,
                "gabarit": -20,
            },
        ),
    ),

    # 4) Открытая 25-й вал
    "open_25": PriceSystemConfig(
        code="open_25",
        title="Відкрита система 25-й вал",
        section_title="Відкрита 25мм вал",
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -35,
            },
        ),
    ),

    # 5) Открытая 25-й вал ДЕНЬ-НОЧЬ
    "open_25_dn": PriceSystemConfig(
        code="open_25_dn",
        title="Відкрита 25мм вал, день-ніч",
        section_title="Відкрита 25мм день-ніч",
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -30,
            },
        ),
    ),

    # 6) Louvolite 32-й вал
    "open_louvolite_32": PriceSystemConfig(
        code="open_louvolite_32",
        title="Відкрита Louvolite 32 вал",
        section_title="Відкрита Louvolite 32мм",
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -42,
            },
        ),
    ),

    # 7) Пружинний механізм відкритий
    "spring_open": PriceSystemConfig(
        code="spring_open",
        title="Відкрита пружинна система",
        section_title="Відкрита пружинна",
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -35,
            },
        ),
    ),

    # 8) Пружинная закрытая, П-образні направляючі
    "spring_closed_p": PriceSystemConfig(
        code="spring_closed_p",
        title="Закрита пружинна, П-профіль",
        section_title="Закрита пружинна П-профіль",
        width_rule=WidthRule(
            canonical="shtapik",
            default_input="shtapik",
            offsets_to_canonical={
                "shtapik": 0,
                "gabarit": -20,
            },
        ),
    ),

    # 9) Открытая 47-й вал
    "open_47": PriceSystemConfig(
        code="open_47",
        title="Відкрита система, 47-й вал",
        section_title="Відкрита 47мм вал",
        width_rule=WidthRule(
            canonical="fabric",
            default_input="fabric",
            offsets_to_canonical={
                "fabric": 0,
                "gabarit": -50,
            },
        ),
    ),
}


# -------------------------------------------------------------------
#  Внутренний метод загрузки секции из прайса
# -------------------------------------------------------------------
def _load_price_table_for_system(
    cfg: PriceSystemConfig,
    *,
    google_sheet_url: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict:
    url = google_sheet_url or PRICE_SHEET_URL
    parsed = parse_first_sheet_price_section(
        google_sheet_url=url,
        section_title=cfg.section_title,
        title_prefix="Фальш",       # У тебя ВСЕ системы в группе "Фальш"
        min_merged_width=12,
        search_cols=6,
        force_refresh=force_refresh,
    )
    return parsed


# -------------------------------------------------------------------
#  ПОЛУЧИТЬ СПИСОК ТКАНЕЙ ДЛЯ СИСТЕМЫ
# -------------------------------------------------------------------
def list_fabrics_for_system(
    system_code: str,
    *,
    google_sheet_url: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict:
    if system_code not in SYSTEMS:
        raise ValueError(f"Unknown system '{system_code}'")

    cfg = SYSTEMS[system_code]
    table = _load_price_table_for_system(cfg, google_sheet_url, force_refresh)

    return {
        "system_code": cfg.code,
        "system_title": cfg.title,
        "section_title": cfg.section_title,
        "width_bands": table.get("width_bands") or [],
        "fabrics": table.get("fabrics") or [],
        "magnets_price_eur": str(table.get("magnets_price_eur") or "0.00"),
    }


# -------------------------------------------------------------------
#  РАСЧЁТ ЦЕНЫ ДЛЯ СИСТЕМЫ
# -------------------------------------------------------------------
def preview_price_for_system(
    system_code: str,
    fabric_name: str,
    width_mm: int,
    height_mm: int,
    *,
    width_input_kind: Optional[WidthKind] = None,
    magnets: bool = False,
    google_sheet_url: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict:
    if system_code not in SYSTEMS:
        raise ValueError(f"Unknown system '{system_code}'")

    cfg = SYSTEMS[system_code]
    used_kind = width_input_kind or cfg.width_rule.default_input

    # 1) Преобразовать ширину в канон (по ткани)
    canonical_width = cfg.width_rule.to_canonical(width_mm, width_input_kind)

    # 2) Загрузить секцию из гугл-прайса
    table = _load_price_table_for_system(cfg, google_sheet_url, force_refresh)
    bands = table["width_bands"]
    fabrics = table["fabrics"]
    magnets_price_base = table["magnets_price_eur"]

    # 3) Определить ценовую полосу по ширине
    band_idx = pick_width_band(bands, canonical_width)
    if band_idx is None:
        raise ValueError("Ширина поза діапазонами прайсу")

    # 4) Найти ткань
    fabric = next((f for f in fabrics if f["name"].lower() == fabric_name.lower()), None)
    if not fabric:
        raise ValueError("Тканину не знайдено в цій системі")

    # 5) Цена по полосе
    base_cell = fabric["prices_by_band"][band_idx]
    if base_cell is None:
        raise ValueError("Ціна відсутня у вибраній смузі")

    base_price = Q(base_cell)

    # 6) Наценка по высоте
    gabarit_limit = fabric["gabarit_limit_mm"] or 0
    if height_mm <= gabarit_limit:
        surcharge = Q("0.00")
    else:
        over = height_mm - gabarit_limit
        steps = (over + (cfg.height_surcharge_step_mm - 1)) // cfg.height_surcharge_step_mm
        surcharge = round_money(base_price * cfg.height_surcharge_pct * Q(int(steps)))

    # 7) Магниты
    magnets_price = magnets_price_base if (magnets and cfg.magnets_supported) else Q("0.00")

    subtotal = round_money(base_price + surcharge + magnets_price)

    return {
        "system_code": cfg.code,
        "system_title": cfg.title,
        "fabric_name": fabric["name"],
        "width_input_kind": used_kind,
        "width_mm_input": width_mm,
        "width_mm_canonical": canonical_width,
        "height_mm_gabarit": height_mm,
        "band_index": band_idx,
        "band_label": bands[band_idx],
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": gabarit_limit,
        "base_price_eur": str(round_money(base_price)),
        "surcharge_height_eur": str(surcharge),
        "magnets_price_eur": str(round_money(magnets_price)),
        "subtotal_eur": str(subtotal),
    }
