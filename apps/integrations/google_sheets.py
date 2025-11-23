# -*- coding: utf-8 -*-
# EN: Google Sheets price parser (sections, fabrics, price preview)
# UA: Парсер прайсу Google Sheets (секції, тканини, прев'ю ціни)

from __future__ import annotations

import re
from typing import List, Dict, Optional

from openpyxl.worksheet.worksheet import Worksheet

import apps.constants as sc
from .google_sheets_core import (
    _download_workbook,
    _row_values,
    _to_decimal,
    round_money,
    Q,
    logger,
    col_letter_to_index,
    get_money_value,
    get_str_values,
    
)


def _norm_title(s: Optional[str]) -> str:
    """
    EN: Normalize title for comparison.
    UA: Нормалізує заголовок для порівняння.
    """
    return (s or "").strip().lower()


# ========= HELPERS / SECTION FINDERS =========

def find_sections_merged(
    ws: Worksheet,
    *,
    min_merged_width: int = 12,
) -> List[Dict]:
    """
    UA: Знаходить секції лише за merged-заголовками в одному рядку.
    EN: Find sections only by one-line merged headers (width >= min_merged_width).
    Returns: [{"title": str, "row": int, "col": int}, ...]
    """
    sections: List[Dict] = []
    seen = set()

    for rng in ws.merged_cells.ranges:
        if rng.min_row == rng.max_row:
            width = rng.max_col - rng.min_col + 1
            if width >= min_merged_width:
                v = ws.cell(row=rng.min_row, column=rng.min_col).value
                if isinstance(v, str) and v.strip():
                    key = (rng.min_row, rng.min_col)
                    if key not in seen:
                        seen.add(key)
                        sections.append(
                            {
                                "title": v.strip(),
                                "row": rng.min_row,
                                "col": rng.min_col,
                            }
                        )

    sections.sort(key=lambda x: (x["row"], x["col"]))
    return sections


def find_sections_by_headers(
    ws: Worksheet,
    *,
    title_prefix: str = "",
    min_merged_width: int = 0,   # kept for compatibility, not used
    search_cols: int = 6,
    case_insensitive: bool = True,
) -> List[Dict]:
    """
    UA: Шукає секції за текстовими заголовками (без прив'язки до merged-ячейок).
        Використовується для пошуку рядків типу:
            "Фальш-ролети, біла система"
            "Фальш-ролети, коричнева система"
            ...
    EN: Find sections by textual headers (no dependency on merged cells).
    Returns: [{"title": str, "row": int, "col": int}, ...]
    """
    sections: List[Dict] = []

    prefix_norm = _norm_title(title_prefix)
    for r in range(1, ws.max_row + 1):
        for c in range(1, search_cols + 1):
            v = ws.cell(row=r, column=c).value
            if not isinstance(v, str):
                continue
            raw = v.strip()
            if not raw:
                continue

            norm = raw.lower() if case_insensitive else raw

            if prefix_norm and not norm.startswith(prefix_norm):
                continue

            # Heuristic: must contain word "система"
            if "система" not in norm:
                continue

            sections.append(
                {
                    "title": raw,
                    "row": r,
                    "col": c,
                }
            )
            break

    sections.sort(key=lambda x: (x["row"], x["col"]))
    return sections


def pick_width_band(width_bands: List[str], width_mm: int) -> Optional[int]:
    """
    UA: Визначає індекс смуги ширини за текстом ('До 400мм', '401–450' ...).
    EN: Chooses band index from textual ranges.
    """
    for i, b in enumerate(width_bands):
        b = str(b).replace(" ", "").replace("мм", "")
        if b.startswith("До"):
            try:
                limit = int(re.sub(r"^До", "", b))
                if width_mm <= limit:
                    return i
            except Exception as e:
                logger.error("pick_width_band failed: %s", e, exc_info=True)
                pass
        else:
            m = re.match(r"(\d+)[–-](\d+)", b)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if lo <= width_mm <= hi:
                    return i
    return None


# ========= PARSE ONE PRICE SECTION =========

def parse_sheet_price_section(
    google_sheet_url: str,
    sheet_name: str,
    section_title: str,
    *,
    gabarit_width_flag: Optional[bool] = None,
    width_mm: int = None,
    fabric_name: str  = None,
    gabarit_height_mm: int  = None,
) -> Dict:
    """
    UA: Парсить ТІЛЬКИ вибрану секцію на вказаному листі.
    EN: Parse ONLY selected section on given sheet.

    Структура як у "Фальш-ролети":
      - зверху блоку: заголовок "Фальш-ролети, біла система" тощо;
      - далі кілька пояснювальних рядків;
      - рядок заголовків з "Тканина", "Висота рулону / тканини", "Габаритна висота ...";
      - наступний рядок: ширинні смуги;
      - далі: тканини до пустого рядка або наступного заголовку-секції.
    """
    result = {}
    
    wb = _download_workbook(google_sheet_url, force_refresh=False)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook")

    ws = wb[sheet_name]

    all_sections = find_sections_by_headers(
        ws,
        title_prefix="",
        min_merged_width=0,
        search_cols=6,
        case_insensitive=True,
    )
    
    result["sheet_name"]=sheet_name or ""
    result["sections"]=all_sections or None
    
    if not section_title:
        return result
    

    wanted_norm = _norm_title(section_title)
    target = next(
        (s for s in all_sections if _norm_title(s["title"]) == wanted_norm),
        None,
    )
    if not target:
        raise ValueError(f"Section '{section_title}' not found on sheet '{sheet_name}'")

    sections_sorted = sorted(all_sections, key=lambda x: (x["row"], x["col"]))
    idx = sections_sorted.index(target)
    start_row = target["row"]
    end_row = (
        sections_sorted[idx + 1]["row"] - 1
        if idx + 1 < len(sections_sorted)
        else ws.max_row
    )

    # 2) Find header row inside section
    header_row: Optional[int] = None
    for r in range(start_row, min(end_row, ws.max_row) + 1):
        vals = _row_values(ws, r)
        joined = " ".join([x or "" for x in vals]).lower()
        if "тканина" in joined and "висота" in joined and "габарит" in joined:
            header_row = r
            break

    if not header_row:
        raise RuntimeError(
            f"Header row not found in section '{section_title}' on sheet '{sheet_name}'"
        )

    # 3) Determine column index where width bands start
    header_vals = _row_values(ws, header_row)
    width_hdr_idx = None
    for i, v in enumerate(header_vals):
        if isinstance(v, str) and "ширина" in v.lower():
            width_hdr_idx = i
            break
    if width_hdr_idx is None:
        # Fallback: after third column
        width_hdr_idx = 3

    width_row = header_row + 1
    width_row_vals = _row_values(ws, width_row)
    width_bands = [v for v in width_row_vals[width_hdr_idx:] if v]

    # 5) Fabrics list
    fabrics: List[Dict] = []
    r = width_row + 1
    while r <= end_row:
        vals = _row_values(ws, r)

        if not any(vals):
            break

        name = (vals[0] or "").strip() if len(vals) > 0 else ""
        if not name:
            r += 1
            continue

        roll_h = _to_decimal(vals[1]) if len(vals) > 1 else None
        gabarit_limit = _to_decimal(vals[2]) if len(vals) > 2 else None

        price_cells = vals[width_hdr_idx:]
        prices = [
            (_to_decimal(pc) if _to_decimal(pc) is not None else None)
            for pc in price_cells
        ]

        fabrics.append(
            {
                "name": name,
                "roll_height_mm": int(roll_h) if roll_h is not None else None,
                "gabarit_limit_mm": int(gabarit_limit) if gabarit_limit is not None else None,
                "prices_by_band": prices,
            }
        )
        r += 1
    
    result["section_title"]=section_title or ""
    result["fabrics"]=fabrics or None
    result["section"]=target or ""
    
    if not width_mm or not gabarit_height_mm:
        return result
    
    real_width_mm = width_mm
    if sheet_name == sc.SheetNameFalshi:
        if gabarit_height_mm:
            real_width_mm = width_mm - 4
        
    idx = pick_width_band(width_bands, real_width_mm)
    if idx is None:
        raise ValueError("Ширина поза діапазонами прайсу")

    fabric = next(
        (f for f in fabrics if f["name"].lower() == fabric_name.lower()),
        None,
    )
    if not fabric:
        raise ValueError("Тканину не знайдено у вибраній секції")

    base_cell = fabric["prices_by_band"][idx]
    if base_cell is None:
        raise ValueError("Ціна відсутня у вибраній смузі")

    base = Q(base_cell)

    limit = fabric["gabarit_limit_mm"] or 0
    if gabarit_height_mm <= limit:
        surcharge = Q("0.00")
    else:
        over = gabarit_height_mm - limit
        steps = (over + 99) // 100  # кожні 10см, заокруглення догори
        surcharge = round_money(base * Q("0.10") * Q(int(steps)))



    
    # 6) Extra magnets price (for Falshi sheet only)
    magnets_price_eur = None
    comment_system = None
    
    if sheet_name == sc.SheetNameFalshi:
        logger.info(f"start_row = {start_row} header_row = {header_row}")
        magnets_price_eur = get_money_value(ws, header_row-1, col_letter_to_index("D"))
        comment_system = get_str_values(ws, header_row-3, header_row-1, 1, 1)

        result["magnets_price_eur"] = magnets_price_eur
        result["comment_system"] = comment_system
    
    result["gabarit_limit_mm"]=limit or None
    result["band_index"]=idx or None
    result["band_label"] = width_bands[idx] if width_bands and idx < len(width_bands) else None
    result["base_price_eur"]=str(round_money(base)) if base else None
    result["surcharge_height_eur"]=str(surcharge) if surcharge else None
    
    return result


# ========= PRICE PREVIEW / FABRIC PARAMS =========

def price_preview_section(
    google_sheet_url: str,
    sheet_name: str,
    section_title: str,
    fabric_name: str,
    width_mm: int,
    gabarit_height_mm: int,
    gabarit_width_flag: bool,
) -> Dict:
    """
    EN: Calculate price preview for given fabric and dimensions.
    UA: Розрахунок прев'ю ціни для заданої тканини та розмірів.
    """
    parsed = parse_sheet_price_section(
        google_sheet_url=google_sheet_url,
        sheet_name=sheet_name,
        section_title=section_title,
        min_merged_width=12,
        force_refresh=False,
        gabarit_width_flag=gabarit_width_flag,
    )

    width_for_price = width_mm  # hook for future width_input_dim logic

    bands = parsed["width_bands"]
    idx = pick_width_band(bands, width_for_price)
    if idx is None:
        raise ValueError("Ширина поза діапазонами прайсу")

    fabrics = parsed.get("fabrics") or []
    fabric = next(
        (f for f in fabrics if f["name"].lower() == fabric_name.lower()),
        None,
    )
    if not fabric:
        raise ValueError("Тканину не знайдено у вибраній секції")

    base_cell = fabric["prices_by_band"][idx]
    if base_cell is None:
        raise ValueError("Ціна відсутня у вибраній смузі")

    base = Q(base_cell)

    limit = fabric["gabarit_limit_mm"] or 0
    if gabarit_height_mm <= limit:
        surcharge = Q("0.00")
    else:
        over = gabarit_height_mm - limit
        steps = (over + 99) // 100  # кожні 10см, заокруглення догори
        surcharge = round_money(base * Q("0.10") * Q(int(steps)))

    magnets_price = parsed.get("magnets_price_eur") or Q("0.00")

    return {
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": limit,
        "band_index": idx,
        "band_label": bands[idx],
        "base_price_eur": str(round_money(base)),
        "surcharge_height_eur": str(surcharge),
        "magnets_price_eur": str(round_money(magnets_price)),
    }
