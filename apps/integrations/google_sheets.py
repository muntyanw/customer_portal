# -*- coding: utf-8 -*-
# EN: Google Sheets helpers (public sheet -> download XLSX, parse first sheet, price preview)
# UA: Хелпери для Google Sheets (публічний доступ -> XLSX, парсинг першої вкладки, прев'ю ціни)
from __future__ import annotations
import io, os, re, json, time, requests, hashlib
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from django.conf import settings

Q = Decimal
CACHE_TTL_SECONDS = 300  # 5 минут; можно увеличить/уменьшить
CACHE_DIR = getattr(settings, "SHEETS_CACHE_DIR", os.path.join(settings.BASE_DIR, "tmp", "sheets_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

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
    except Exception:
        return {}
    
def _write_meta(meta_path: str, data: dict):
    tmp = meta_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, meta_path)

def _download_workbook(google_sheet_url: str, force_refresh: bool = False):
    """
    Download XLSX with ETag/TTL cache.
    """
    url = _xlsx_export_url(google_sheet_url)
    xlsx_path, meta_path = _cache_keys(google_sheet_url)
    meta = _read_meta(meta_path)
    etag = meta.get("etag")
    ts = meta.get("ts", 0)

    # TTL: если есть свежий файл — читаем локально без сети
    if not force_refresh and os.path.exists(xlsx_path) and time.time() - ts < CACHE_TTL_SECONDS:
        with open(xlsx_path, "rb") as f:
            return load_workbook(io.BytesIO(f.read()), data_only=True)

    headers = {}
    if etag and not force_refresh:
        headers["If-None-Match"] = etag

    resp = requests.get(url, timeout=30, headers=headers)
    if resp.status_code == 304 and os.path.exists(xlsx_path):
        # контент не менялся — обновим ts и используем кеш
        meta["ts"] = time.time()
        _write_meta(meta_path, meta)
        with open(xlsx_path, "rb") as f:
            return load_workbook(io.BytesIO(f.read()), data_only=True)

    resp.raise_for_status()
    content = resp.content
    # сохранить xlsx
    with open(xlsx_path, "wb") as f:
        f.write(content)

    # сохранить etag + ts, если есть
    new_etag = resp.headers.get("ETag")
    meta = {"etag": new_etag, "ts": time.time()}
    _write_meta(meta_path, meta)

    return load_workbook(io.BytesIO(content), data_only=True)


def list_sheet_titles(google_sheet_url: str, *, force_refresh: bool = False) -> List[str]:
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    return wb.sheetnames

def _merged_cell_spans(ws: Worksheet):
    for rng in ws.merged_cells.ranges:
        yield (rng.min_row, rng.min_col, rng.max_row, rng.max_col)

def find_sections_by_headers(
    ws: Worksheet,
    title_prefix: str,
    *,
    min_merged_width: int = 12,
    search_cols: int = 6,
    case_insensitive: bool = True,
) -> List[Dict]:
    """
    UA: Пошук секцій універсально:
      1) як об'єднані заголовки у одному рядку (ширина >= min_merged_width)
      2) як текстові заголовки, що ПОЧИНАЮТЬСЯ з title_prefix (у перших search_cols колонках)
    Повертає: [{"title": str, "row": int, "col": int}...]

    :param ws: аркуш Excel (openpyxl)
    :param title_prefix: префікс заголовка (наприклад, "Фальш")
    :param min_merged_width: мінімальна кількість злитих комірок у рядку для визнання заголовком
    :param search_cols: скільки перших колонок сканувати для текстових заголовків
    :param case_insensitive: порівнювати префікс без урахування регістру
    """
    def _norm(s: Optional[str]) -> str:
        s = (s or "").strip()
        return s.lower() if case_insensitive else s

    pfx = _norm(title_prefix)
    sections: List[Dict] = []
    seen = set()  # для дедупликации: (row, col, title_norm)

    # --- (1) merged headers у один рядок ---
    for rng in ws.merged_cells.ranges:
        if rng.min_row == rng.max_row:
            width = rng.max_col - rng.min_col + 1
            if width >= min_merged_width:
                v = ws.cell(row=rng.min_row, column=rng.min_col).value
                if isinstance(v, str) and v.strip():
                    v_norm = _norm(v)
                    # must start with prefix
                    if not pfx or v_norm.startswith(pfx):
                        key = (rng.min_row, rng.min_col, v_norm)
                        if key not in seen:
                            seen.add(key)
                            sections.append({
                                "title": v.strip(),
                                "row": rng.min_row,
                                "col": rng.min_col,
                            })

    # --- (2) fallback: текстові заголовки без merge ---
    # перебираємо рядки і перші search_cols колонок; беремо ті, що ПОЧИНАЮТЬСЯ з префіксу
    max_r = ws.max_row or 0
    for r in range(1, max_r + 1):
        for c in range(1, max(1, search_cols) + 1):
            v = ws.cell(row=r, column=c).value
            if not isinstance(v, str):
                continue
            if not v.strip():
                continue
            v_norm = _norm(v)
            if pfx and not v_norm.startswith(pfx):
                continue
            key = (r, c, v_norm)
            if key in seen:
                continue
            seen.add(key)
            sections.append({
                "title": v.strip(),
                "row": r,
                "col": c,
            })

    # впорядкуємо за позицією зверху-вниз, зліва-направо
    sections.sort(key=lambda x: (x["row"], x["col"]))
    return sections

def _row_values(ws: Worksheet, row: int, start_col: int = 1, end_col: Optional[int] = None):
    if end_col is None:
        end_col = ws.max_column
    vals = []
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
    except Exception:
        return None

def parse_first_sheet_price(google_sheet_url: str, force_refresh: bool = False) -> Dict:
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    ws = wb[wb.sheetnames[0]]

    sections = find_sections_by_headers(
        ws,
        title_prefix="Фальш",      # ← важливо: секції починаються з цього префікса
        min_merged_width=12,
        search_cols=6,
        case_insensitive=True,
    )

    # locate header row by keywords
    header_row = None
    for r in range(1, min(ws.max_row, 250)):
        row = _row_values(ws, r)
        joined = " ".join([x or "" for x in row])
        if "Тканина" in joined and "Висота рулону" in joined and "Габаритна висота до" in joined:
            header_row = r
            break
    if not header_row:
        raise RuntimeError("Header row not found on first sheet")

    header_vals = _row_values(ws, header_row)
    # find index of "Ширина готового виробу"
    try:
        width_hdr_idx = header_vals.index(next(v for v in header_vals if v and "Ширина" in v))
    except StopIteration:
        width_hdr_idx = 3  # fallback
    width_row = header_row + 1
    width_bands = [v for v in _row_values(ws, width_row)[width_hdr_idx + 1 - 1:] if v]

    # magnets price — search above header
    magnets_price = Q("0.00")
    for r in range(max(1, header_row - 8), header_row + 1):
        j = " ".join([x or "" for x in _row_values(ws, r)]).lower()
        if "магніт" in j:
            for cell in _row_values(ws, r):
                d = _to_decimal(cell)
                if d is not None:
                    magnets_price = d
                    break
            break

    fabrics = []
    r = width_row + 1
    while r <= ws.max_row:
        vals = _row_values(ws, r)
        if not any(vals):
            break
        name = (vals[0] or "").strip()
        if not name:
            r += 1
            continue
        roll_h = _to_decimal(vals[1])
        gabarit_limit = _to_decimal(vals[2])
        price_cells = vals[width_hdr_idx + 1 - 1:]
        prices = [(_to_decimal(pc) if _to_decimal(pc) is not None else None) for pc in price_cells]
        fabrics.append({
            "name": name,
            "roll_height_mm": int(roll_h) if roll_h is not None else None,
            "gabarit_limit_mm": int(gabarit_limit) if gabarit_limit is not None else None,
            "prices_by_band": prices,  # same order as width_bands
        })
        r += 1

    return {
        "sections": sections,
        "width_bands": width_bands,
        "fabrics": fabrics,
        "magnets_price_eur": magnets_price,
    }

def pick_width_band(width_bands: List[str], width_mm: int) -> Optional[int]:
    """
    UA: Визначаємо індекс смуги ширини за текстом ('До 400мм', '401–450' ...).
    """
    for i, b in enumerate(width_bands):
        b = str(b).replace(" ", "").replace("мм", "")
        if b.startswith("До"):
            try:
                limit = int(re.sub(r"^До", "", b))
                if width_mm <= limit:
                    return i
            except Exception:
                pass
        else:
            m = re.match(r"(\d+)[–-](\d+)", b)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if lo <= width_mm <= hi:
                    return i
    return None

def fabric_params_first(google_sheet_url: str, fabric_name: str, *, force_refresh: bool = False):
    parsed = parse_first_sheet_price(google_sheet_url, force_refresh=force_refresh)
    f = next((x for x in parsed["fabrics"] if x["name"].lower() == fabric_name.lower()), None)
    if not f:
        return None
    return {
        "roll_height_mm": f["roll_height_mm"],
        "gabarit_limit_mm": f["gabarit_limit_mm"]
    }

def price_preview_first(google_sheet_url: str, fabric_name: str, width_mm: int,
                        gabarit_height_mm: int, magnets: bool, *, force_refresh: bool = False) -> Dict:
    parsed = parse_first_sheet_price(google_sheet_url, force_refresh=force_refresh)
    bands = parsed["width_bands"]
    idx = pick_width_band(bands, width_mm)
    if idx is None:
        raise ValueError("Ширина поза діапазонами прайсу")

    fabric = next((f for f in parsed["fabrics"] if f["name"].lower() == fabric_name.lower()), None)
    if not fabric:
        raise ValueError("Тканину не знайдено")

    base_cell = fabric["prices_by_band"][idx]
    if base_cell is None:
        raise ValueError("Ціна відсутня у вибраній смузі")

    base = Q(base_cell)

    limit = fabric["gabarit_limit_mm"] or 0
    if gabarit_height_mm <= limit:
        surcharge = Q("0.00")
    else:
        over = gabarit_height_mm - limit
        steps = (over + 99) // 100  # кожні 10см, заокруглення до більшого
        surcharge = round_money(base * Q("0.10") * Q(int(steps)))

    magnets_price = Q(parsed["magnets_price_eur"]) if magnets else Q("0.00")
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


def parse_first_sheet_price_section(
    google_sheet_url: str,
    section_title: str,
    *,
    title_prefix: str = "Фальш",
    min_merged_width: int = 12,
    search_cols: int = 6,
    force_refresh: bool = False,
) -> Dict:
    """
    Возвращает структуру ТОЛЬКО для выбранной секции: width_bands, fabrics, magnets_price_eur.
    Алгоритм:
      - Находим список секций (merged+prefix).
      - Выбираем секцию с title == section_title (без учета регистра и лишних пробелов).
      - В пределах этой секции ниже по строкам ищем локальный header ('Тканина'...'Габаритна висота до'...'Ширина...').
      - Следующая строка — ширинные полосы (bands).
      - Затем до пустой строки или до начала следующей секции — ткани/цены.
    """
    wb = _download_workbook(google_sheet_url, force_refresh=force_refresh)
    ws = wb[wb.sheetnames[0]]

    # 1) Все секции
    sections = find_sections_by_headers(
        ws,
        title_prefix=title_prefix,
        min_merged_width=min_merged_width,
        search_cols=search_cols,
        case_insensitive=True,
    )
    norm = lambda s: (s or "").strip().lower()
    target = next((s for s in sections if norm(s["title"]) == norm(section_title)), None)
    if not target:
        raise ValueError("Секцію не знайдено")

    start_row = target["row"]
    # граница секции — строка перед следующей секцией или конец листа
    sections_sorted = sorted(sections, key=lambda x: (x["row"], x["col"]))
    idx = sections_sorted.index(target)
    end_row = (sections_sorted[idx+1]["row"] - 1) if idx + 1 < len(sections_sorted) else ws.max_row

    # 2) Внутри блока ищем header-строку
    header_row = None
    for r in range(start_row, min(end_row, ws.max_row) + 1):
        vals = _row_values(ws, r)
        joined = " ".join([x or "" for x in vals])
        if "Тканина" in joined and "Висота рулону" in joined and "Габаритна висота до" in joined:
            header_row = r
            break
    if not header_row:
        raise RuntimeError("Не знайдено заголовок таблиці у секції")

    header_vals = _row_values(ws, header_row)
    # индекс колонки "Ширина готового виробу..."
    try:
        width_hdr_idx = header_vals.index(next(v for v in header_vals if v and "Ширина" in v))
    except StopIteration:
        width_hdr_idx = 3  # fallback

    width_row = header_row + 1
    width_bands = [v for v in _row_values(ws, width_row)[width_hdr_idx + 1 - 1:] if v]

    # 3) Цена магнітів — попробуем найти над хедером секции
    magnets_price = Q("0.00")
    for r in range(max(start_row, header_row - 8), header_row + 1):
        j = " ".join([x or "" for x in _row_values(ws, r)]).lower()
        if "магніт" in j:
            for cell in _row_values(ws, r):
                d = _to_decimal(cell)
                if d is not None:
                    magnets_price = d
                    break
            break

    # 4) Ткани (только в пределах секции)
    fabrics = []
    r = width_row + 1
    while r <= end_row:
        vals = _row_values(ws, r)
        if not any(vals):
            break  # пустая строка — конец таблицы секции
        name = (vals[0] or "").strip()
        if not name:
            r += 1
            continue
        roll_h = _to_decimal(vals[1])
        gabarit_limit = _to_decimal(vals[2])
        price_cells = vals[width_hdr_idx + 1 - 1:]
        prices = [(_to_decimal(pc) if _to_decimal(pc) is not None else None) for pc in price_cells]
        fabrics.append({
            "name": name,
            "roll_height_mm": int(roll_h) if roll_h is not None else None,
            "gabarit_limit_mm": int(gabarit_limit) if gabarit_limit is not None else None,
            "prices_by_band": prices,
        })
        r += 1

    return {
        "width_bands": width_bands,
        "fabrics": fabrics,
        "magnets_price_eur": round_money(magnets_price),
        "section": target,
    }