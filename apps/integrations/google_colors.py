# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

from django.conf import settings

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials

from googleapiclient.errors import HttpError
from google.auth.exceptions import TransportError
from httplib2 import ServerNotFoundError



def _get_sheets_service():
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


# === Кешування локальної копії таблиці з кольорами тканин ===

# Можна переоприділити шлях у settings.FABRIC_COLORS_CACHE_FILE
FABRIC_COLORS_CACHE_FILE = Path(
    getattr(
        settings,
        "FABRIC_COLORS_CACHE_FILE",
        Path(settings.BASE_DIR) / "cache" / "fabric_colors_cache.json",
    )
)

# Мінімальний інтервал між зверненнями до Google Sheets (в секундах)
CACHE_MIN_INTERVAL_SECONDS = 15 * 60  # 15 хвилин


def _ensure_cache_dir_exists() -> None:
    """UA: Створює директорію для кешу, якщо її ще немає."""
    FABRIC_COLORS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _hash_values(values) -> str:
    """UA: Рахує хеш від масиву values, щоб розуміти, чи змінилися дані."""
    data = json.dumps(values, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def _load_cache_payload() -> Optional[dict]:
    """
    UA: Повертає повний payload з кешу:
        { "values": [...], "hash": "...", "fetched_at": "..." }
    або None, якщо кешу немає / він зламаний.
    """
    if not FABRIC_COLORS_CACHE_FILE.exists():
        return None
    try:
        with FABRIC_COLORS_CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Мінімальна валідація
        if "values" not in data:
            return None
        return data
    except Exception:
        return None


def _save_cached_values(values: list, fetched_at: Optional[datetime] = None) -> None:
    """UA: Зберігає values, їх хеш та час отримання у локальний кеш."""
    _ensure_cache_dir_exists()
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)
    payload = {
        "values": values,
        "hash": _hash_values(values),
        "fetched_at": fetched_at.isoformat(),
    }
    with FABRIC_COLORS_CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _get_fabric_colors_values_with_cache() -> Optional[list]:
    """
    UA: Повертає values з Google Sheets або з локального кешу.

    Логіка:
      1) Читаємо кеш (якщо є). Якщо останній успішний запит був < 5 хвилин тому —
         НЕ йдемо в Google, а одразу повертаємо кеш.
      2) Якщо минуло >= 5 хвилин або кешу немає:
         - пробуємо отримати дані з Google;
         - при успіху зберігаємо нові values + fetched_at і повертаємо їх;
         - при помилці (немає інтернету/Google недоступний) повертаємо кеш,
           якщо він є, або None, якщо кешу немає.
    """
    now = datetime.now(timezone.utc)
    cache_payload = _load_cache_payload()
    cached_values = cache_payload.get("values") if cache_payload else None
    cached_fetched_at: Optional[datetime] = None

    if cache_payload:
        fetched_at_raw = cache_payload.get("fetched_at")
        if isinstance(fetched_at_raw, str):
            try:
                cached_fetched_at = datetime.fromisoformat(fetched_at_raw)
            except ValueError:
                cached_fetched_at = None

    # Якщо кеш є і він "свіжий" (< 5 хвилин), одразу повертаємо його без звернення до Google
    if cached_values is not None and cached_fetched_at is not None:
        age_seconds = (now - cached_fetched_at).total_seconds()
        if age_seconds >= 0 and age_seconds < CACHE_MIN_INTERVAL_SECONDS:
            return cached_values

    # Інакше — пробуємо отримати актуальні дані з Google
    sheet_id = settings.FABRIC_COLORS_SHEET_ID
    sheet_name = getattr(settings, "FABRIC_COLORS_SHEET_NAME", "Лист1")
    range_ = f"{sheet_name}!A:Z"

    try:
        service = _get_sheets_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=range_)
            .execute()
        )
        values = result.get("values", [])

        # Зберігаємо нові дані і час запиту
        _save_cached_values(values, fetched_at=now)
        return values

    except (HttpError, OSError, IOError, ConnectionError, TransportError, ServerNotFoundError) as e:
        # Google недоступний — намагаємося повернути кеш, якщо він є
        if cached_values is not None:
            return cached_values
        return None


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

    values = _get_fabric_colors_values_with_cache()
    if not values:
        return []

    # перший рядок — заголовок
    header = values[0]
    data_rows = values[1:]

    # шукаємо колонку з кодами по назві в першому ряду, наприклад "Коди кольорів"
    color_col_idx: Optional[int] = None
    for idx, cell in enumerate(header):
        if isinstance(cell, str):
            lower = cell.lower()
            if "код" in lower and "кол" in lower:
                color_col_idx = idx
                break

    # якщо заголовка немає — вважаємо, що коди у колонці C (index=2)
    if color_col_idx is None:
        color_col_idx = 2

    # шукаємо рядок, де A == fabric_name (без регістру)
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

    # парсимо "01; 02, 03  04" -> ["01", "02", "03", "04"]
    parts: List[str] = []
    tmp = codes_raw.replace(",", ";").replace(" ", ";")
    for part in tmp.split(";"):
        p = part.strip()
        if p:
            parts.append(p)

    return parts
