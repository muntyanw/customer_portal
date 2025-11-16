# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional
from django.conf import settings

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def _get_sheets_service():
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


def get_fabric_color_codes(fabric_name: str) -> List[str]:
    """
    UA: Повертає список кодів кольорів для заданої тканини
        з окремої таблиці (sheet FABRIC_COLORS_SHEET_ID).

    Припущення:
      - Назва тканини в колонці A
      - Коди кольорів у певній колонці (наприклад, C або колонка з заголовком).
      - У клітинці з кодами коди розділені комами / крапками з комою / пробілами.
    """
    fabric_name = (fabric_name or "").strip()
    if not fabric_name:
        return []

    service = _get_sheets_service()
    sheet_id = settings.FABRIC_COLORS_SHEET_ID
    sheet_name = getattr(settings, "FABRIC_COLORS_SHEET_NAME", "Лист1")

    # читаем "много": первые, скажем, 2000 строк, колонки A:Z
    range_ = f"{sheet_name}!A:Z"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return []

    # ищем строку с нужной тканью в колонке A
    header = values[0] if values else []
    data_rows = values[1:]

    # ищем колонку с кодами по названию в первом ряду, например "Коди кольорів"
    color_col_idx: Optional[int] = None
    for idx, cell in enumerate(header):
        if isinstance(cell, str) and "код" in cell.lower() and "кол" in cell.lower():
            color_col_idx = idx
            break

    # если заголовка нет — допустим, что коды в колонке C (index=2) или любой фиксированной
    if color_col_idx is None:
        color_col_idx = 2  # колонка C по умолчанию

    # ищем строку, где A == fabric_name (без регистра)
    target_row = None
    for row in data_rows:
        name_cell = row[0] if len(row) > 0 else ""
        if isinstance(name_cell, str) and name_cell.strip().lower() == fabric_name.lower():
            target_row = row
            break

    if not target_row:
        return []

    codes_raw = target_row[color_col_idx] if len(target_row) > color_col_idx else ""
    if not isinstance(codes_raw, str):
        return []

    # парсим "01; 02, 03  04" -> ["01", "02", "03", "04"]
    parts = []
    tmp = codes_raw.replace(",", ";").replace(" ", ";")
    for part in tmp.split(";"):
        p = part.strip()
        if p:
            parts.append(p)

    return parts
