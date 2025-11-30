# -*- coding: utf-8 -*-
# EN: Google Sheets price parser (sections, fabrics, price preview)
# UA: Парсер прайсу Google Sheets (секції, тканини, прев'ю ціни)

from __future__ import annotations

import re
from typing import List, Dict, Optional, Any


from openpyxl.worksheet.worksheet import Worksheet

from apps.sheet_config import sheetName, sheetConfigs, getConfigBySheetName, sheetConfig
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
    min_merged_width: int = 0,  # kept for compatibility, not used
    search_cols: int = 6,
    case_insensitive: bool = True,
    sheet_name: str = "",  # 🔹 новый параметр
) -> List[Dict]:
    """
    UA: Шукає секції за текстовими заголовками (без прив'язки до merged-ячейок).
        Використовується для пошуку рядків типу:
            "Фальш-ролети, біла система"
            "Фальш-ролети, коричнева система"
            ...
        Додатково: рядок вважається секцією, якщо перші 5 символів
        збігаються з першими 5 символами назви аркуша (sheet_name).
    EN: Find sections by textual headers (no dependency on merged cells).
        Additionally, a row is considered a section only if the first
        5 characters match the first 5 characters of sheet_name.
    Returns: [{"title": str, "row": int, "col": int}, ...]
    """
    sections: List[Dict] = []

    prefix_norm = _norm_title(title_prefix)

    # 🔹 Нормализуем sheet_name один раз
    sheet_prefix_norm = ""
    if sheet_name:
        sheet_norm_full = sheet_name.strip()
        if case_insensitive:
            sheet_norm_full = sheet_norm_full.lower()
        sheet_prefix_norm = sheet_norm_full[:4]

    for r in range(1, ws.max_row + 1):
        for c in range(1, search_cols + 1):
            v = ws.cell(row=r, column=c).value
            if not isinstance(v, str):
                continue
            raw = v.strip()
            if not raw:
                continue

            norm = raw.lower() if case_insensitive else raw

            # 🔹 Условие по title_prefix, как было
            if prefix_norm and not norm.startswith(prefix_norm):
                continue

            # 🔹 Новое условие: первые 4 символов совпадают с sheet_name
            if sheet_prefix_norm:
                if norm[:4] != sheet_prefix_norm:
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
    fabric_name: str = None,
    gabarit_height_mm: int = None,
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
      Може бути кілька таких під-таблиць (коли ширини не вміщаються в один блок).
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
        sheet_name=sheet_name,
    )

    result["sheet_name"] = sheet_name or ""
    result["sections"] = all_sections or None

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

    idx_section = sections_sorted.index(target)
    start_row = target["row"]
    end_row = (
        sections_sorted[idx_section + 1]["row"] - 1
        if idx_section + 1 < len(sections_sorted)
        else ws.max_row
    )

    # 2) Find ALL header rows inside section
    #    (support one or multiple header blocks "Тканина / Висота / Габарит...")
    header_rows: List[int] = []
    for r in range(start_row, min(end_row, ws.max_row) + 1):
        vals = _row_values(ws, r)
        joined = " ".join([x or "" for x in vals]).lower()
        if "тканина" in joined and "висота" in joined and "габарит" in joined:
            header_rows.append(r)

    if not header_rows:
        raise RuntimeError(
            f"Header row not found in section '{section_title}' on sheet '{sheet_name}'"
        )

    # Для сумісності далі використовуємо перший заголовок як "основний"
    header_rows = sorted(header_rows)
    header_row = header_rows[0]

    # 3) Determine width bands and fabrics (support multiple sub-tables)
    #    Ми НЕ дублюємо парсинг: кожен рядок читається рівно один раз,
    #    а ціни по одній тканині з різних під-таблиць просто додаються в кінець.
    all_width_bands: List[Any] = []

    fabrics_map: Dict[str, Dict] = {}  # key: name.lower()
    fabric_order: List[str] = []  # to preserve first-seen order

    for i_hr, hr in enumerate(header_rows):
        header_vals = _row_values(ws, hr)

        # Find the first "ширина" column in this header block
        width_hdr_idx = None
        for i, v in enumerate(header_vals):
            if isinstance(v, str) and "ширина" in v.lower():
                width_hdr_idx = i
                break
        if width_hdr_idx is None:
            # Fallback: after third column
            width_hdr_idx = 3

        width_row = hr + 1
        width_row_vals = _row_values(ws, width_row)
        width_bands_part = [v for v in width_row_vals[width_hdr_idx:] if v]
        all_width_bands.extend(width_bands_part)

        # границя поточної під-таблиці: до наступного header_row або end_row
        next_header_row = (
            header_rows[i_hr + 1] if i_hr + 1 < len(header_rows) else end_row + 1
        )

        # 5) Fabrics list for this sub-table
        r = width_row + 1
        while r < next_header_row and r <= end_row:
            vals = _row_values(ws, r)

            # порожній рядок — кінець даних поточної під-таблиці
            if not any(vals):
                break

            name = (vals[0] or "").strip() if len(vals) > 0 else ""
            if not name:
                r += 1
                continue

            roll_h = _to_decimal(vals[1]) if len(vals) > 1 else None
            gabarit_limit = _to_decimal(vals[2]) if len(vals) > 2 else None

            price_cells = vals[width_hdr_idx:]
            prices_part = [
                (_to_decimal(pc) if _to_decimal(pc) is not None else None)
                for pc in price_cells
            ]

            key = name.lower()

            if key not in fabrics_map:
                fabrics_map[key] = {
                    "name": name,
                    "roll_height_mm": int(roll_h) if roll_h is not None else None,
                    "gabarit_limit_mm": (
                        int(gabarit_limit) if gabarit_limit is not None else None
                    ),
                    "prices_by_band": prices_part,
                }
                fabric_order.append(key)
            else:
                f = fabrics_map[key]
                # дозаповнюємо висоту/габарит, якщо раніше були None
                if f["roll_height_mm"] is None and roll_h is not None:
                    f["roll_height_mm"] = int(roll_h)
                if f["gabarit_limit_mm"] is None and gabarit_limit is not None:
                    f["gabarit_limit_mm"] = int(gabarit_limit)
                # додаємо нові ціни в кінець діапазону
                f["prices_by_band"].extend(prices_part)

            r += 1

    fabrics: List[Dict] = [fabrics_map[k] for k in fabric_order]
    width_bands = all_width_bands

    result["section_title"] = section_title or ""
    result["fabrics"] = fabrics or None
    result["section"] = target or ""

    if not width_mm or not gabarit_height_mm:
        return result

    real_width_mm = width_mm
    cg = getConfigBySheetName(sheet_name)
    gb_width_mm = width_mm
    if cg.gbDiffWidthMm:
        gb_width_mm = width_mm + cg.gbDiffWidthMm
        if gabarit_width_flag:
            real_width_mm = width_mm - cg.gbDiffWidthMm
            gb_width_mm = width_mm
        result["GbDiffWidthMm"] = cg.gbDiffWidthMm
    else:
        result["GbDiffWidthMm"] = 0

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
    if sheet_name == sheetName.falshi:
        result["magnets_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        result["comment_system_red"] = get_str_values(
            ws, header_row - 3, header_row - 3, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 2, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.falshiDn:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 3, header_row - 3, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 2, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.vidkr19yiBesta:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 9, header_row - 9, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 8, header_row - 6, 1, 1
        )
        result["metal_cord_fix_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("D")
        )
        result["cord_copper_barrel_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("D")
        )
        result["magnets_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        result["top_pvc_clip_pair_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("N")
        )
        result["op_pvc_bar_tape_price_eur"] = get_money_value(  # как у тебя
            ws, header_row - 2, col_letter_to_index("N")
        )

    if sheet_name == sheetName.vidkr19yiBestaDn:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 8, header_row - 7, 1, 1
        )
        result["comment_system_red"] += "<br/>" + get_str_values(
            ws,
            header_row - 4,
            header_row - 4,
            col_letter_to_index("E"),
            col_letter_to_index("E"),
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 7, header_row - 5, 1, 1
        )
        result["metal_cord_fix_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("D")
        )
        result["top_pvc_clip_pair_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("D")
        )
        result["top_bar_scotch_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )

    if sheet_name == sheetName.zakrytaPloskaBesta:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 6, header_row - 6, 1, 1
        )
        result["comment_system_red"] += "<br/>" + get_str_values(
            ws, header_row - 4, header_row - 4, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 5, header_row - 5, 1, 1
        )
        result["comment_system_green"] += "<br/>" + get_str_values(
            ws, header_row - 3, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.zakrytaPloskaBestaDn:
        if "біла" in section_title:
            result["comment_system_red"] = get_str_values(
                ws, header_row - 5, header_row - 5, 1, 1
            )
            result["comment_system_green"] = get_str_values(
                ws, header_row - 4, header_row - 2, 1, 1
            )
        else:
            result["comment_system_red"] = get_str_values(
                ws, header_row - 6, header_row - 6, 1, 1
            )
            result["comment_system_red"] += "<br/>" + get_str_values(
                ws, header_row - 4, header_row - 4, 1, 1
            )
            result["comment_system_green"] = get_str_values(
                ws, header_row - 5, header_row - 5, 1, 1
            )
            result["comment_system_green"] += "<br/>" + get_str_values(
                ws, header_row - 3, header_row - 2, 1, 1
            )

    if sheet_name == sheetName.zakrytaPpodibBesta:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 7, header_row - 7, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 6, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.zakrytaPpodibnaBestaDn:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 6, header_row - 6, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 5, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.vidkr25yiBesta:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 8, header_row - 8, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 7, header_row - 4, 1, 1
        )

        result["cord_pvc_tension_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("D")
        )
        result["cord_copper_barrel_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("D")
        )
        result["magnets_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        result["metal_kronsht_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("N")
        )
        result["bottom_wide_bar_price_eur_mp"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("N")
        )

    if sheet_name == sheetName.vidkr25yiDn:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 6, header_row - 6, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 5, header_row - 3, 1, 1
        )

        result["metal_cord_fix_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        
    if sheet_name == sheetName.vidkrPruzhynna:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 5, header_row - 5, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 4, header_row - 2, 1, 1
        )

    if sheet_name == sheetName.zakrPruzhPpodibBesta:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 7, header_row - 7, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 6, header_row - 2, 1, 1
        )
        
    if sheet_name == sheetName.vidkr32yiLouvolitte:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 8, header_row - 8, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 7, header_row - 5, 1, 1
        )

        result["cord_pvc_tension_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("D")
        )
        result["cord_copper_barrel_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("D")
        )
        result["magnets_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        result["bottom_wide_bar_price_eur_mp"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("N")
        )
        
    if sheet_name == sheetName.vidkr47yiDvyhunAboLouvolit:
        result["comment_system_red"] = get_str_values(
            ws, header_row - 8, header_row - 8, 1, 1
        )
        result["comment_system_green"] = get_str_values(
            ws, header_row - 7, header_row - 5, 1, 1
        )

        result["cord_pvc_tension_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("D")
        )
        result["cord_copper_barrel_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("D")
        )
        result["magnets_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("D")
        )
        result["motor_no_remote_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("N")
        )
        result["motor_with_remote_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("N")
        )
        result["bottom_wide_bar_price_eur_mp"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("N")
        )
        result["remote_5ch_price_eur"] = get_money_value(
            ws, header_row - 3, col_letter_to_index("X")
        )
        result["remote_15ch_price_eur"] = get_money_value(
            ws, header_row - 2, col_letter_to_index("X")
        )
        result["middle_bracket_price_eur"] = get_money_value(
            ws, header_row - 1, col_letter_to_index("X")
        )
        
       
        
    result["gabarit_limit_mm"] = limit or None
    result["gb_width_mm"] = gb_width_mm or None
    result["band_index"] = idx or None
    result["band_label"] = (
        width_bands[idx] if width_bands and idx < len(width_bands) else None
    )
    result["base_price_eur"] = str(round_money(base)) if base else None
    result["surcharge_height_eur"] = str(surcharge) if surcharge else None

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
    

# ========= COMPONENTS SHEET (Комплектація) =========


def parse_components_sheet(
    google_sheet_url: str,
    sheet_name: str = "Комплектація",
    *,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    EN: Parse simple components list from 'Комплектація' sheet.
    UA: Парсить простий список комплектуючих з аркуша 'Комплектація'.

    Очікувана структура аркуша:
        Найменування | Од. вим. | Колір | Вартість, Євро
        <name>       | <unit>   | <color> | <price>

    Повертає:
        {
          "sheet_name": "Комплектація",
          "items": [
             {
               "name": "...",
               "unit": "шт",
               "color": "Білий",
               "price_eur": "2.199",
             },
             ...
          ],
          "names": [... унікальні найменування ...],
          "units": [... унікальні одиниці виміру ...],
          "colors": [... унікальні кольори ...],
        }
    """
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook")

    ws = wb[sheet_name]

    # 1) Знаходимо рядок заголовків
    header_row = None
    for r in range(1, ws.max_row + 1):
        vals = _row_values(ws, r)
        joined = " ".join([str(v) for v in vals if v]).strip().lower()
        if not joined:
            continue

        # шукаємо одночасно "найменування" і "вартість"
        if "найменування" in joined and "варт" in joined:
            header_row = r
            break

    if header_row is None:
        raise RuntimeError(
            f"Header row not found on sheet '{sheet_name}' (expect 'Найменування' / 'Вартість')"
        )

    header_vals = _row_values(ws, header_row)

    def _find_col(header_candidates) -> Optional[int]:
        """
        EN: Find column index by header text candidates.
        UA: Знаходить індекс колонки за можливими варіантами заголовка.
        """
        for idx, val in enumerate(header_vals):
            if not isinstance(val, str):
                continue
            norm = val.strip().lower()
            for cand in header_candidates:
                if cand in norm:
                    return idx
        return None

    # очікувані колонки
    name_idx = _find_col(["найменування"])
    unit_idx = _find_col(["од.", "од. вим", "од.вим"])
    color_idx = _find_col(["колір"])
    price_idx = _find_col(["вартість", "варт.", "ціна"])

    # як fallback — стандартний порядок колонок: 0,1,2,3
    if name_idx is None:
        name_idx = 0
    if unit_idx is None:
        unit_idx = 1
    if color_idx is None:
        color_idx = 2
    if price_idx is None:
        price_idx = 3

    items: List[Dict[str, Any]] = []
    names_set = set()
    units_set = set()
    colors_set = set()

    # 2) Читаємо всі рядки після заголовка
    for r in range(header_row + 1, ws.max_row + 1):
        vals = _row_values(ws, r)
        if not any(vals):
            # порожній рядок вважаємо кінцем таблиці
            continue

        name = (vals[name_idx] or "").strip() if len(vals) > name_idx else ""
        if not name:
            # пропускаємо рядки без найменування
            continue

        unit = (vals[unit_idx] or "").strip() if len(vals) > unit_idx else ""
        color = (vals[color_idx] or "").strip() if len(vals) > color_idx else ""

        raw_price = vals[price_idx] if len(vals) > price_idx else None
        price_dec = _to_decimal(raw_price)

        if price_dec is None:
            # якщо немає ціни — такий рядок не віддаємо на фронт
            logger.warning(
                "parse_components_sheet: empty/invalid price on row %s (name=%r)",
                r,
                name,
            )
            continue

        item = {
            "name": name,
            "unit": unit,
            "color": color,
            "price_eur": str(price_dec),
        }
        items.append(item)

        names_set.add(name)
        if unit:
            units_set.add(unit)
        if color:
            colors_set.add(color)

    result: Dict[str, Any] = {
        "sheet_name": sheet_name,
        "items": items,
        "names": sorted(names_set),
        "units": sorted(units_set),
        "colors": sorted(colors_set),
    }
    return result
