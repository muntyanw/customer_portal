# -*- coding: utf-8 -*-
# apps/api/v1/pricing_views.py
from typing import Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response
from apps.integrations.google_colors import get_fabric_color_codes
from apps.sheet_config import sheetConfigs, sheetConfig, getConfigBySheetName

from apps.integrations.google_sheets import (
    parse_sheet_price_section,
    parse_components_sheet,
    parse_fabrics_sheet,
    parse_mosquito_price_sheet,
    parse_mosquito_components_sheet,
    build_mosquito_warnings,
    select_mosquito_catalog_product,
)


from apps.integrations.google_sheets_core import (
    list_sheet_titles,
    Q,
    round_money,
    _to_decimal,
)
from apps.orders.services_currency import get_current_usd_rate

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
        
        filtered_titles = []
        for t in titles:
            try:
                cfg = getConfigBySheetName(t)
            except KeyError:
                # Skip sheets that are not roller systems (e.g. fabric price sheet)
                continue
            if (cfg.display if cfg else 1) != 0:
                filtered_titles.append(t)

        
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
    fabric_height_flag = data.get("fabric_height_flag")

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
        
    def _to_bool(val):
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on")
        return bool(val)

    system_is_flat = "плоска" in system_sheet.lower()
    width_by_fabric = system_is_flat and _to_bool(gabarit_width_flag)
    height_by_fabric = system_is_flat and _to_bool(fabric_height_flag)

    if width_by_fabric:
        width_mm += 44
        gabarit_width_flag = False
    if height_by_fabric:
        gabarit_height_mm += 37

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


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def fabrics_list(request):
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)
    sheet = (request.query_params.get("sheet") or "Тканини до ролет").strip()
    force = _flag(request.query_params.get("force_refresh"))
    try:
        parsed = parse_fabrics_sheet(
            google_sheet_url=url,
            sheet_name=sheet,
            force_refresh=force,
        )
        return Response(parsed, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("fabrics_list failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def fabric_preview(request):
    data = request.data or {}
    url = data.get("url")
    sheet = (data.get("sheet") or "Тканини до ролет").strip()
    fabric_name = (data.get("fabric_name") or "").strip()
    width_mm = data.get("width_mm")
    height_mm = data.get("height_mm")
    quantity = data.get("quantity") or 1
    cut_enabled = True

    try:
        width_mm = int(width_mm)
        height_mm = int(height_mm)
        quantity = int(quantity)
    except Exception:
        return Response({"detail": "width_mm, height_mm, quantity мають бути цілими числами."},
                        status=status.HTTP_400_BAD_REQUEST)

    if not url or not fabric_name:
        return Response({"detail": "Потрібні параметри: url, fabric_name."},
                        status=status.HTTP_400_BAD_REQUEST)
    if width_mm <= 0 or height_mm <= 0 or quantity <= 0:
        return Response({"detail": "Ширина/висота/кількість мають бути > 0."},
                        status=status.HTTP_400_BAD_REQUEST)

    parsed = parse_fabrics_sheet(google_sheet_url=url, sheet_name=sheet, force_refresh=False)
    items = parsed.get("items") or []
    fabric = next((f for f in items if (f.get("name") or "").lower() == fabric_name.lower()), None)
    if not fabric:
        return Response({"detail": "Тканину не знайдено у вибраній секції"},
                        status=status.HTTP_400_BAD_REQUEST)

    roll_width = int(fabric.get("roll_width_mm") or 0)
    if roll_width and width_mm > roll_width:
        return Response({"detail": "Ширина перевищує ширину рулону."},
                        status=status.HTTP_400_BAD_REQUEST)

    included_height = int(fabric.get("included_height_mm") or 0)
    price_eur_mp = _to_decimal(fabric.get("price_eur_mp") or "0")
    base_price = price_eur_mp * Q(str(width_mm)) / Q("1000")
    extra_steps = 0
    if included_height and height_mm > included_height:
        extra_steps = (height_mm - included_height + 99) // 100
    multiplier = Q("1") + Q("0.10") * Q(int(extra_steps))
    unit_price = round_money(base_price * multiplier)

    cut_price_eur = _to_decimal(parsed.get("extra_cut_price_eur") or "0")
    cut_total = cut_price_eur * Q(str(quantity))

    total = round_money(unit_price * Q(str(quantity)) + cut_total)

    return Response(
        {
            "roll_width_mm": roll_width,
            "included_height_mm": included_height,
            "price_eur_mp": str(price_eur_mp),
            "unit_price_eur": str(unit_price),
            "extra_steps": int(extra_steps),
            "cut_price_eur": str(cut_price_eur),
            "cut_enabled": bool(cut_enabled),
            "cut_total_eur": str(round_money(cut_total)),
            "quantity": int(quantity),
            "total_eur": str(total),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def mosquito_products_list(request):
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)
    sheet = (request.query_params.get("sheet") or "Прайс").strip()
    force = _flag(request.query_params.get("force_refresh"))
    try:
        parsed = parse_mosquito_price_sheet(
            google_sheet_url=url,
            sheet_name=sheet,
            force_refresh=force,
        )
        parsed["usd_rate"] = str(get_current_usd_rate())
        return Response(parsed, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("mosquito_products_list failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mosquito_preview(request):
    data = request.data or {}
    url = data.get("url")
    sheet = (data.get("sheet") or "Прайс").strip()
    product_type = (data.get("product_type") or "").strip()
    color = (data.get("color") or "").strip()
    mesh_type = (data.get("mesh_type") or "").strip()
    width_mm = data.get("width_mm")
    height_mm = data.get("height_mm")
    quantity = data.get("quantity") or 1

    try:
        width_mm = int(width_mm)
        height_mm = int(height_mm)
        quantity = int(quantity)
    except Exception:
        return Response(
            {"detail": "width_mm, height_mm, quantity мають бути цілими числами."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not url or not product_type or not color or not mesh_type:
        return Response(
            {"detail": "Потрібні параметри: url, product_type, color, mesh_type."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if width_mm <= 0 or height_mm <= 0 or quantity <= 0:
        return Response(
            {"detail": "Ширина/висота/кількість мають бути > 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    parsed = parse_mosquito_price_sheet(google_sheet_url=url, sheet_name=sheet, force_refresh=False)
    product = select_mosquito_catalog_product(parsed.get("products") or [], product_type, color, height_mm)
    if not product:
        return Response({"detail": "Виріб або колір не знайдено у прайсі."}, status=status.HTTP_400_BAD_REQUEST)

    price_usd_sqm = _to_decimal((product.get("mesh_prices_usd_sqm") or {}).get(mesh_type))
    if price_usd_sqm is None:
        return Response({"detail": "Для цього виробу немає ціни по вибраному полотну."}, status=status.HTTP_400_BAD_REQUEST)

    actual_area = Q(str(width_mm)) * Q(str(height_mm)) / Q("1000000")
    min_area = _to_decimal(product.get("min_area_sqm") or "0") or Q("0")
    calc_area = actual_area if actual_area >= min_area else min_area
    subtotal_usd = round_money(calc_area * price_usd_sqm * Q(str(quantity)))
    usd_rate = get_current_usd_rate()
    total_uah = round_money(subtotal_usd * Q(str(usd_rate or 0)))
    warnings = build_mosquito_warnings(
        product_type=product_type,
        mesh_type=mesh_type,
        width_mm=width_mm,
        height_mm=height_mm,
        area_sqm=calc_area,
    )

    return Response(
        {
            "product_type": product_type,
            "color": color,
            "mesh_type": mesh_type,
            "price_usd_sqm": str(price_usd_sqm),
            "actual_area_sqm": str(round_money(actual_area)),
            "min_area_sqm": str(min_area),
            "calc_area_sqm": str(round_money(calc_area)),
            "quantity": quantity,
            "subtotal_usd": str(subtotal_usd),
            "usd_rate": str(usd_rate),
            "total_uah": str(total_uah),
            "dimension_labels": product.get("dimension_labels") or {},
            "fiberglass_only": bool(product.get("fiberglass_only")),
            "requires_sliding_side": bool(product.get("requires_sliding_side")),
            "warnings": warnings,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def mosquito_components_list(request):
    url = request.query_params.get("url")
    if not url:
        return Response({"detail": "Missing url"}, status=status.HTTP_400_BAD_REQUEST)
    sheet = (request.query_params.get("sheet") or "Комплектація").strip()
    force = _flag(request.query_params.get("force_refresh"))
    try:
        parsed = parse_mosquito_components_sheet(
            google_sheet_url=url,
            sheet_name=sheet,
            force_refresh=force,
        )
        parsed["usd_rate"] = str(get_current_usd_rate())
        return Response(parsed, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("mosquito_components_list failed: %s", e, exc_info=True)
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
