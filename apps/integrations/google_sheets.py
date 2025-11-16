# -*- coding: utf-8 -*-
# EN: Google Sheets helpers (public sheet -> download XLSX, parse sheets, price preview)
# UA: Хелпери для Google Sheets (публічний доступ -> XLSX, парсинг вкладок, прев'ю ціни)

from __future__ import annotations

import io
import os
import re
import json
import time
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional

import requests
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from django.conf import settings

import logging
logger = logging.getLogger("sheets")

#logger.debug("Downloading sheet %s", google_sheet_url)
#logger.info("Loaded workbook for sheet %s", sheet_name)
#ogger.warning("Fallback: header row not found exactly in %s", section_title)
#logger.error("Google Sheets error: %s", e, exc_info=True)


Q = Decimal
CACHE_TTL_SECONDS = 300  # 5 min; can be changed

CACHE_DIR = getattr(
    settings,
    "SHEETS_CACHE_DIR",
    os.path.join(settings.BASE_DIR, "tmp", "sheets_cache"),
)
os.makedirs(CACHE_DIR, exist_ok=True)


def _norm_title(s: Optional[str]) -> str:
    """
    EN: Normalize title for comparison.
    UA: Нормалізує заголовок для порівняння.
    """
    return (s or "").strip().lower()

# ---------- money / cache helpers ----------

def round_money(x: Decimal) -> Decimal:
    return x.quantize(Q("0.01"), rounding=ROUND_HALF_UP)


def _xlsx_export_url(google_sheet_url: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
    if not m:
        raise ValueError("Bad Google Sheets URL")
    sheet_id = m.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"


def _cache_keys(google_sheet_url: str):
    key = hashlib.sha256(google_sheet_url.encode("utf-8")).hexdigest()
    xlsx_path = os.path.join(CACHE_DIR, f"{key}.xlsx")
    meta_path = os.path.join(CACHE_DIR, f"{key}.json")
    return xlsx_path, meta_path


def _read_meta(meta_path: str) -> dict:
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("_cache_keys failed: %s", e, exc_info=True)
        return {}


def _write_meta(meta_path: str, data: dict):
    tmp = meta_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, meta_path)


def _download_workbook(google_sheet_url: str, force_refresh: bool = False):
    """
    EN: Download XLSX with ETag/TTL cache.
    UA: Завантажує XLSX з кешем за ETag/TTL.
    """
    url = _xlsx_export_url(google_sheet_url)
    xlsx_path, meta_path = _cache_keys(google_sheet_url)
    meta = _read_meta(meta_path)
    etag = meta.get("etag")
    ts = meta.get("ts", 0)

    # TTL: if file is fresh - use local copy
    if (
        not force_refresh
        and os.path.exists(xlsx_path)
        and time.time() - ts < CACHE_TTL_SECONDS
    ):
        with open(xlsx_path, "rb") as f:
            return load_workbook(io.BytesIO(f.read()), data_only=True)

    headers = {}
    if etag and not force_refresh:
        headers["If-None-Match"] = etag

    resp = requests.get(url, timeout=30, headers=headers)
    if resp.status_code == 304 and os.path.exists(xlsx_path):
        meta["ts"] = time.time()
        _write_meta(meta_path, meta)
        with open(xlsx_path, "rb") as f:
            return load_workbook(io.BytesIO(f.read()), data_only=True)

    resp.raise_for_status()
    content = resp.content
    with open(xlsx_path, "wb") as f:
        f.write(content)

    new_etag = resp.headers.get("ETag")
    meta = {"etag": new_etag, "ts": time.time()}
    _write_meta(meta_path, meta)

    return load_workbook(io.BytesIO(content), data_only=True)


# ---------- public: list sheet titles ----------

def list_sheet_titles(google_sheet_url: str, *, force_refresh: bool = False) -> List[str]:
    """
    EN: Return list of sheet names (tabs).
    UA: Повертає список назв вкладок.
    """
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    return wb.sheetnames


# ---------- helpers for parsing ----------

def _row_values(
    ws: Worksheet,
    row: int,
    start_col: int = 1,
    end_col: Optional[int] = None,
) -> List[Optional[str]]:
    if end_col is None:
        end_col = ws.max_column
    vals: List[Optional[str]] = []
    for c in range(start_col, end_col + 1):
        v = ws.cell(row=row, column=c).value
        if v is None or isinstance(v, str):
            vals.append(v)
        else:
            vals.append(str(v))
    return vals


def _to_decimal(x) -> Optional[Decimal]:
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    try:
        return Q(s)
    except Exception as e:
        logger.error("_to_decimal failed: %s", e, exc_info=True)
        return None


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


# ========= UNIVERSAL SECTION PARSER (ANY SHEET) =========

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


def parse_sheet_price_section(
    google_sheet_url: str,
    sheet_name: str,
    section_title: str,
    *,
    min_merged_width: int = 12,   # оставляем в сигнатуре, но внутри не используем
    force_refresh: bool = False,
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
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook")

    ws = wb[sheet_name]

    # 1) Находим все секции на листе тем же способом, что и API
    all_sections = find_sections_by_headers(
        ws,
        title_prefix="",      # не фильтруем по префиксу
        min_merged_width=0,   # не используем
        search_cols=6,
        case_insensitive=True,
    )

    # Нормализуем названия
    wanted_norm = _norm_title(section_title)
    target = next(
        (s for s in all_sections if _norm_title(s["title"]) == wanted_norm),
        None,
    )
    if not target:
        raise ValueError(f"Section '{section_title}' not found on sheet '{sheet_name}'")

    # Определяем границы секции по соседним заголовкам
    sections_sorted = sorted(all_sections, key=lambda x: (x["row"], x["col"]))
    idx = sections_sorted.index(target)
    start_row = target["row"]
    end_row = (
        sections_sorted[idx + 1]["row"] - 1
        if idx + 1 < len(sections_sorted)
        else ws.max_row
    )

    # 2) Ищем строку заголовков внутри секции (более гибко)
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

    # 3) Определяем колонку начала ширинных смуг
    header_vals = _row_values(ws, header_row)
    width_hdr_idx = None
    for i, v in enumerate(header_vals):
        if isinstance(v, str) and "ширина" in v.lower():
            width_hdr_idx = i
            break
    if width_hdr_idx is None:
        # Fallback: после третьей колонки
        width_hdr_idx = 3

    width_row = header_row + 1
    width_row_vals = _row_values(ws, width_row)
    width_bands = [v for v in width_row_vals[width_hdr_idx:] if v]

    # 4) Цена магнітів (ищем в тексті над заголовком)
    magnets_price = Q("0.00")
    search_from = max(start_row, header_row - 8)
    for r in range(search_from, header_row + 1):
        row_vals = _row_values(ws, r)
        joined = " ".join([x or "" for x in row_vals]).lower()
        if "магніт" in joined:
            for cell in row_vals:
                d = _to_decimal(cell)
                if d is not None:
                    magnets_price = d
                    break
            break

    # 5) Список тканей
    fabrics: List[Dict] = []
    r = width_row + 1
    while r <= end_row:
        vals = _row_values(ws, r)

        # если строка полностью пустая — считаем, что секция закончилась
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

    return {
        "sheet_name": sheet_name,
        "section_title": section_title,
        "width_bands": width_bands,
        "fabrics": fabrics,
        "magnets_price_eur": round_money(magnets_price),
        "section": target,
    }

# ---------- width conversion hook (future place for system-specific logic) ----------

def _convert_width_for_system(
    sheet_name: str,
    width_mm: int,
    gabarit_width_flag: bool,
) -> int:
    """
    EN: TEMP: width is used as-is. Here later we can plug in system-specific
        conversions (gabarit width vs fabric width etc.).
    UA: ПОКИ ЩО: просто повертаємо width_mm без змін.
    """
    return width_mm


# ---------- price preview for sheet + section ----------

def price_preview_section(
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
) -> Dict:
    """
    EN: Generic price preview for ANY sheet+section.
    UA: Універсальний прев’ю для будь-якої вкладки/секції.
    """
    parsed = parse_sheet_price_section(
        google_sheet_url=google_sheet_url,
        sheet_name=sheet_name,
        section_title=section_title,
        min_merged_width=12,
        force_refresh=force_refresh,
    )

    width_for_price = _convert_width_for_system(
        sheet_name=parsed["sheet_name"],
        width_mm=width_mm,
        gabarit_width_flag=gabarit_width_flag,
    )

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

    magnets_price = parsed["magnets_price_eur"] if magnets else Q("0.00")
    subtotal = round_money(base + surcharge + magnets_price)

    return {
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": limit,
        "band_index": idx,
        "band_label": bands[idx],
        "base_price_eur": str(round_money(base)),
        "surcharge_height_eur": str(surcharge),
        "magnets_price_eur": str(round_money(magnets_price)),
        "subtotal_eur": str(subtotal),
    }


def fabric_params_for_sheet_section(
    google_sheet_url: str,
    sheet_name: str,
    section_title: str,
    fabric_name: str,
    *,
    force_refresh: bool = False,
) -> Optional[Dict]:
    """
    EN: Return basic params for given fabric on given sheet+section.
    UA: Повертає параметри тканини для вкладки/секції.
    """
    parsed = parse_sheet_price_section(
        google_sheet_url=google_sheet_url,
        sheet_name=sheet_name,
        section_title=section_title,
        min_merged_width=12,
        force_refresh=force_refresh,
    )
    fabrics = parsed.get("fabrics") or []
    fabric = next(
        (f for f in fabrics if f["name"].lower() == fabric_name.lower()),
        None,
    )
    if not fabric:
        return None
    return {
        "roll_height_mm": fabric["roll_height_mm"],
        "gabarit_limit_mm": fabric["gabarit_limit_mm"],
    }
    

def find_sections_by_headers(
    ws: Worksheet,
    *,
    title_prefix: str = "",
    min_merged_width: int = 0,   # не используем, оставлен для совместимости
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

            # Если задан префикс — проверяем startswith
            if prefix_norm:
                if not norm.startswith(prefix_norm):
                    continue

            # Чтобы не цеплять любые строки, фильтруем по слову "система"
            # (подходит под твой кейс "Фальш-ролети, ... система").
            if "система" not in norm:
                continue

            sections.append(
                {
                    "title": raw,
                    "row": r,
                    "col": c,
                }
            )
            # В строке найден один заголовок — дальше по колонкам этой строки не идём
            break

    # На всякий случай отсортируем по строке / колонке
    sections.sort(key=lambda x: (x["row"], x["col"]))
    return sections

