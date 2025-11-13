# -*- coding: utf-8 -*-
from typing import List, Dict, Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response

# Импортируем функции парсинга
from apps.integrations.google_sheets import (
    list_sheet_titles,
    fabric_params_first,
    price_preview_first,
    parse_first_sheet_price_section,
    find_sections_by_headers,
    _download_workbook,  # используем для быстрого доступа к листу
)


# --------- Утилита: булевый флаг из query/body ---------
def _flag(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


# ========= СТАРЫЕ (совместимость) =========

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def sheets_list(request):
    """
    GET /api/v1/pricing/sheets-list?url=...&force_refresh=1
    Возвращает список названий вкладок (листов) книги.
    """
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)

    force = _flag(request.query_params.get("force_refresh"))
    try:
        titles = list_sheet_titles(url, force_refresh=force)
        return Response({"sheets": titles})
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def fabrics_first(request):
    """
    GET /api/v1/pricing/fabrics-first?url=...&force_refresh=1

    Для совместимости со старым фронтом:
    - Возвращает список секций первой вкладки (Фальш*)
    - Плюс "плоский" список тканей первой найденной секции (чтобы не ломать старое поведение).
      Новый фронт должен использовать:
        - /pricing/sections-first
        - /pricing/fabrics-first-section?section=...
    """
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)

    force = _flag(request.query_params.get("force_refresh"))
    try:
        wb = _download_workbook(url, force_refresh=force)
        ws = wb[wb.sheetnames[0]]

        # Секции (логика: merged + начинается с "Фальш")
        sections = find_sections_by_headers(
            ws,
            title_prefix="Фальш",
            min_merged_width=12,
            search_cols=6,
            case_insensitive=True,
        )

        # Возьмём ткани из первой секции, если есть (для бэк-компат)
        fabrics = []
        if sections:
            first_section_title = sections[0]["title"]
            parsed = parse_first_sheet_price_section(
                url,
                section_title=first_section_title,
                title_prefix="Фальш",
                min_merged_width=12,
                search_cols=6,
                force_refresh=force,
            )
            fabrics = [{"name": f["name"]} for f in (parsed.get("fabrics") or [])]

        return Response({
            "sections": sections,
            "fabrics": fabrics,  # только для совместимости со старым JS
        })

    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def preview_first(request):
    """
    POST /api/v1/pricing/preview-first
    Body:
      {
        "url": "<GoogleSheetUrl>",
        "fabric_name": "<string>",
        "width_mm": <int>,
        "gabarit_height_mm": <int>,
        "magnets": <bool>,          # optional
        "force_refresh": <bool>     # optional
      }
    """
    data = request.data or {}

    url = data.get("url")
    fabric_name = (data.get("fabric_name") or "").strip()
    width_mm = data.get("width_mm")
    gabarit_height_mm = data.get("gabarit_height_mm")
    magnets = _flag(data.get("magnets"))

    # force_refresh: body или query
    force = _flag(data.get("force_refresh")) or _flag(request.query_params.get("force_refresh"))

    # числовая валидация
    try:
        width_mm = int(width_mm)
        gabarit_height_mm = int(gabarit_height_mm)
    except Exception:
        return Response(
            {"detail": "width_mm та gabarit_height_mm мають бути цілими числами."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not url or not fabric_name:
        return Response(
            {"detail": "Потрібні параметри: url, fabric_name."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if width_mm <= 0 or gabarit_height_mm <= 0:
        return Response(
            {"detail": "Ширина/висота мають бути > 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        preview = price_preview_first(
            google_sheet_url=url,
            fabric_name=fabric_name,
            width_mm=width_mm,
            gabarit_height_mm=gabarit_height_mm,
            magnets=magnets,
            force_refresh=force,
        )
        params = fabric_params_first(
            google_sheet_url=url,
            fabric_name=fabric_name,
            force_refresh=force,
        ) or {}

        preview.update({"fabric_params": params})
        return Response(preview, status=status.HTTP_200_OK)

    except ValueError as ve:
        return Response({"detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"Помилка розрахунку: {e}"}, status=status.HTTP_502_BAD_GATEWAY)


# ========= НОВЫЕ (секция → ткани) =========

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def sections_first(request):
    """
    GET /api/v1/pricing/sections-first?url=...&force_refresh=1
    Возвращает секции первой вкладки (по правилу: merged в одну строку И начинается с "Фальш").
    """
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)

    force = _flag(request.query_params.get("force_refresh"))
    try:
        wb = _download_workbook(url, force_refresh=force)
        ws = wb[wb.sheetnames[0]]

        sections = find_sections_by_headers(
            ws,
            title_prefix="Фальш",
            min_merged_width=12,
            search_cols=6,
            case_insensitive=True,
        )
        return Response({"sections": sections})
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def fabrics_first_section(request):
    """
    GET /api/v1/pricing/fabrics-first-section?url=...&section=...&force_refresh=1
    Возвращает ткани и полосы ширин ТОЛЬКО выбранной секции.
    """
    url = request.query_params.get("url")
    section = request.query_params.get("section")
    if not url or not section:
        return Response({"detail": "Missing url or section"}, status=status.HTTP_400_BAD_REQUEST)

    force = _flag(request.query_params.get("force_refresh"))
    try:
        parsed = parse_first_sheet_price_section(
            google_sheet_url=url,
            section_title=section,
            title_prefix="Фальш",
            min_merged_width=12,
            search_cols=6,
            force_refresh=force,
        )
        fabrics = [{"name": f["name"]} for f in (parsed.get("fabrics") or [])]
        return Response({
            "width_bands": parsed.get("width_bands") or [],
            "fabrics": fabrics,
            "magnets_price_eur": str(parsed.get("magnets_price_eur", "0.00")),
            "section": parsed.get("section"),
        })
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
