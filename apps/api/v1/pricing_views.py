# -*- coding: utf-8 -*-
# apps/api/v1/pricing_views.py
from typing import Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response
from apps.integrations.google_colors import get_fabric_color_codes
from apps.sheet_config import sheetName, sheetConfigs, sheetConfig

from apps.integrations.google_sheets import (
    parse_sheet_price_section,
    parse_components_sheet,
)


from apps.integrations.google_sheets_core import (
    list_sheet_titles,
)

import logging
logger = logging.getLogger("app")

#logger.info("Order created")
#logger.warning("Something suspicious")
#logger.error("Failed to save order", exc_info=True)


def _flag(val: Any) -> bool:
    """EN: Convert value to bool; UA: Перетворення значення на bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "y", "on")
    return False


# ========= NEW: work with ALL sheets (= systems) =========

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def systems_list(request):
    """
    GET /api/v1/pricing/systems-list?url=...&force_refresh=1

    EN: Return list of systems = sheet names.
    UA: Повертає список систем = назв вкладок прайсу.
    """
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)

    force = _flag(request.query_params.get("force_refresh"))
    try:
        titles = list_sheet_titles(url, force_refresh=force)
        
        filtered_titles = [
            t for t in titles
            if sheetConfigs.get(sheetName(t), sheetConfig()).display != 0
        ]

        
        return Response({"systems": filtered_titles})
    except Exception as e:
        logger.error("systems_list failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def system_fabrics(request):
    """
    GET /api/v1/pricing/system-fabrics?url=...&system=...&section=...?force_refresh=1

    Режимы:
      1) Только system:
         -> вернёт список СЕКЦИЙ-КОЛЬОРІВ системы для указанной вкладки.
      2) system + section:
         -> помимо секций вернёт ткани и ширинные полосы выбранной секции.
    """
    url = request.query_params.get("url")
    system = request.query_params.get("system")  # имя вкладки
    section = request.query_params.get("section")  # заголовок секции (строка "Фальш-ролети, біла система")

    if not url or not system:
        return Response({"detail": "Missing url or system"}, status=status.HTTP_400_BAD_REQUEST)

    try:
    
        parsed = parse_sheet_price_section(
            google_sheet_url=url,
            sheet_name=system,
            section_title=section,
        )

        return Response(parsed)

    except Exception as e:
        logger.error("system_fabrics failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def system_preview(request):
    """
    POST /api/v1/pricing/system-preview

    Body:
      {
        "url": "<GoogleSheetUrl>",
        "system_sheet": "<sheet name>",
        "section_title": "<section title>",
        "fabric_name": "<string>",
        "width_mm": <int>,
        "gabarit_height_mm": <int>,
        "gabarit_width_flag": <bool>,
      }
    """
    data = request.data or {}

    url = data.get("url")
    system_sheet = (data.get("system_sheet") or "").strip()
    section_title = (data.get("section_title") or "").strip()
    fabric_name = (data.get("fabric_name") or "").strip()
    width_mm = data.get("width_mm")
    gabarit_height_mm = data.get("gabarit_height_mm")
    gabarit_width_flag = data.get("gabarit_width_flag")

    # ---- numeric validation ----
    try:
        width_mm = int(width_mm)
        gabarit_height_mm = int(gabarit_height_mm)
    except Exception:
        return Response(
            {"detail": "width_mm та gabarit_height_mm мають бути цілими числами."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not url or not system_sheet or not section_title or not fabric_name:
        return Response(
            {
                "detail": "Потрібні параметри: url, system_sheet, section_title, fabric_name."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
        
    if width_mm <= 0 or gabarit_height_mm <= 0:
        return Response(
            {"detail": "Ширина/висота мають бути > 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        preview = parse_sheet_price_section(
            google_sheet_url=url,
            sheet_name=system_sheet,
            section_title=section_title,
            fabric_name=fabric_name,
            width_mm=width_mm,
            gabarit_height_mm=gabarit_height_mm,
            gabarit_width_flag = gabarit_width_flag
        )

        return Response(preview, status=status.HTTP_200_OK)

    except ValueError as ve:
        return Response({"detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"detail": f"Помилка розрахунку: {e}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def fabric_colors(request):
    """
    GET /api/v1/pricing/fabric-colors?fabric=...

    EN: Return list of color codes for fabric.
    UA: Повертає коди кольорів для вибраної тканини.
    """
    fabric = (request.query_params.get("fabric") or "").strip()
    if not fabric:
        return Response({"detail": "Missing fabric"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        codes = get_fabric_color_codes(fabric)
        return Response({"fabric": fabric, "color_codes": codes})
    except Exception as e:
        logger.error("fabric_colors failed: %s", e, exc_info=True)
        return Response({"detail": f"Помилка завантаження кольорів: {e}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def system_config(request):
    """
    GET /api/v1/pricing/system-config?system=...

    Возвращает полный конфиг из SYSTEM_CONFIG для конкретной вкладки.
    """
    system = request.query_params.get("system")
    if not system:
        return Response({"detail": "Missing system"}, status=status.HTTP_400_BAD_REQUEST)

    cfg = get_system_cfg(system)
    return Response({"system": system, "config": cfg})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def components_list(request):
    """
    GET /api/v1/pricing/components-list?url=...&sheet=Комплектація&force_refresh=1

    EN: Return list of components from 'Комплектація' sheet
        + distinct names/units/colors for selects.
    UA: Повертає список комплектуючих з аркуша 'Комплектація'
        + унікальні назви/одиниці/кольори для селектів.
    """
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)

    sheet = (request.query_params.get("sheet") or "Комплектація").strip()
    force = _flag(request.query_params.get("force_refresh"))

    try:
        parsed = parse_components_sheet(
            google_sheet_url=url,
            sheet_name=sheet,
            force_refresh=force,
        )
        return Response(parsed, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("components_list failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
