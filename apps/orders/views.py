# apps/orders/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.db import transaction
from django.contrib import messages
from .models import Order, OrderItem
from apps.accounts.roles import is_manager
import json
from decimal import Decimal, InvalidOperation
from django.http import HttpResponseForbidden
from django.conf import settings

from .models import Order, OrderComponentItem
from .utils_components import parse_components_from_post
from django.urls import reverse

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["title", "description", "attachment"]
        
        
def _get(lst, idx, default=""):
    """EN: Safe list index with default. UA: Безпечне отримання елемента зі списку з дефолтом."""
    return lst[idx] if idx < len(lst) else default


def _to_decimal(value, default="0"):
    """EN: Convert string to Decimal with fallback. UA: Конвертація рядка в Decimal з запасним значенням."""
    value = (value or "").strip()
    if not value:
        value = default
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal(default)

@login_required
def order_list(request):
    """
    EN: List of orders with roller items.
    UA: Список замовлень з тканинними ролетами.
    """
    qs = (
        Order.objects
        .filter(items__isnull=False)   # related_name для позиций ролет
        .distinct()
        .order_by("-created_at")
    )
    context = {
        "orders": qs,
        "list_mode": "rollers",  # флаг для шаблона
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_components_list(request):
    """
    EN: List of orders that have components.
    UA: Список замовлень, у яких є комплектуючі.
    """
    qs = (
        Order.objects
        .filter(component_items__isnull=False)  # related_name для комплектующих
        .distinct()
        .order_by("-created_at")
    )
    context = {
        "orders": qs,
        "list_mode": "components",
    }
    return render(request, "orders/order_list.html", context)

@login_required
def order_create(request):
    """
    Створювати може будь-який аутентифікований користувач.
    Customer — створює для себе; Manager теж може створити собі (або окрему форму зробимо пізніше).
    """
    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.customer = request.user
            obj.save()
            return redirect("orders:list")
    else:
        form = OrderForm()
    return render(request, "orders/create.html", {"form": form})

@login_required
def order_detail(request, pk: int):
    return redirect("orders:builder_edit", pk=pk)


@login_required
def order_update(request, pk: int):
    """
    Customer може редагувати лише свої замовлення (за потреби — тільки певні поля).
    Manager — будь-які.
    """
    if is_manager(request.user):
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, customer=request.user)

    if request.method == "POST":
        form = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            return redirect("orders:list")
    else:
        form = OrderForm(instance=order)
    return render(request, "orders/update.html", {"form": form, "order": order})


PRICE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vjwqhZ0-9SWcN-u8Oa-T6ciNmHfMeHU-c2RTv6axqHs/edit?gid=0#gid=0"


@login_required
@transaction.atomic
def order_builder(request, pk=None):
    """
    Один универсальный билдер:
    - GET + pk=None     → создание заказа (пустой билдер)
    - GET + pk=<id>     → редактирование / просмотр
    - POST + pk=None    → создать заказ + Items
    - POST + pk=<id>    → обновить заказ + Items
    """

    # Получение или создание ордера
    if pk:
        if is_manager(request.user):
            order = get_object_or_404(Order, pk=pk)
        else:
            order = get_object_or_404(Order, pk=pk, customer=request.user)
    else:
        order = None

    # -------------------------------------
    # POST: создание или обновление
    # -------------------------------------
    if request.method == "POST":
        # Если ордера нет — создаём
        if order is None:
            order = Order.objects.create(customer=request.user)

        # Для менеджера можно добавить присвоение customer
        profile = getattr(request.user, "customerprofile", None)
        org = getattr(profile, "organization", None)

        # Удаляем старые Items
        order.items.all().delete()

        # Чтение всех списков (как раньше)
        systems = request.POST.getlist("system_sheet")
        sections = request.POST.getlist("table_section")
        fabrics = request.POST.getlist("fabric_name")
        fabric_colors = request.POST.getlist("fabric_color_code")

        h_list = request.POST.getlist("height_gabarit_mm")
        w_list = request.POST.getlist("width_fabric_mm")

        gw_flags = request.POST.getlist("gabarit_width_flag")

        base_prices = request.POST.getlist("base_price_eur")
        sur_prices = request.POST.getlist("surcharge_height_eur")
        magnets_price_eur = request.POST.getlist("magnets_price_eur")
        magnets_qty = request.POST.getlist("magnets_qty")
        cord_pvc_tension_price_eur = request.POST.getlist("cord_pvc_tension_price_eur")
        cord_pvc_tension_qty = request.POST.getlist("cord_pvc_tension_qty")
        cord_copper_barrel_price_eur = request.POST.getlist("cord_copper_barrel_price_eur")
        cord_copper_barrel_qty = request.POST.getlist("cord_copper_barrel_qty")
        top_pvc_clip_pair_price_eur = request.POST.getlist("top_pvc_clip_pair_price_eur")
        top_pvc_clip_pair_qty = request.POST.getlist("top_pvc_clip_pair_qty")
        top_pvc_bar_tape_price_eur_mp = request.POST.getlist("top_pvc_bar_tape_price_eur_mp")
        top_pvc_bar_tape_qty = request.POST.getlist("top_pvc_bar_tape_qty")
        bottom_wide_bar_price_eur_mp = request.POST.getlist("bottom_wide_bar_price_eur_mp")
        bottom_wide_bar_qty = request.POST.getlist("bottom_wide_bar_qty")
        top_bar_scotch_price_eur = request.POST.getlist("top_bar_scotch_price_eur")
        top_bar_scotch_qty = request.POST.getlist("top_bar_scotch_qty")
        metal_cord_fix_price_eur = request.POST.getlist("metal_cord_fix_price_eur")
        metal_cord_fix_qty = request.POST.getlist("metal_cord_fix_qty")
        middle_bracket_price_eur = request.POST.getlist("middle_bracket_price_eur")
        middle_bracket_qty = request.POST.getlist("middle_bracket_qty")
        remote_15ch_price_eur = request.POST.getlist("remote_15ch_price_eur")
        remote_15ch_qty = request.POST.getlist("remote_15ch_qty")
        remote_5ch_price_eur = request.POST.getlist("remote_5ch_price_eur")
        remote_5ch_qty = request.POST.getlist("remote_5ch_qty")
        motor_with_remote_price_eur = request.POST.getlist("motor_with_remote_price_eur")
        motor_with_remote_qty = request.POST.getlist("motor_with_remote_qty")
        motor_no_remote_price_eur = request.POST.getlist("motor_no_remote_price_eur")
        motor_no_remote_qty = request.POST.getlist("motor_no_remote_qty")
        
        subtotals = request.POST.getlist("subtotal_eur")

        roll_infos = request.POST.getlist("roll_height_info")
        qty_list = request.POST.getlist("quantity")
        control_sides = request.POST.getlist("control_side")
        bottom_fixations = request.POST.getlist("bottom_fixation")
        pvc_planks = request.POST.getlist("pvc_plank")

        # -----------------------------------------
        # Создание всех OrderItem (ГОРАЗДО ЧИЩЕ)
        # -----------------------------------------
        for idx, system_sheet in enumerate(systems):

            OrderItem.objects.create(
                order=order,
                organization=org,
                system_sheet=system_sheet or "",
                table_section=_get(sections, idx, ""),
                fabric_name=_get(fabrics, idx, ""),
                fabric_color_code=_get(fabric_colors, idx, ""),
                height_gabarit_mm=int(_get(h_list, idx, "0")),
                width_fabric_mm=int(_get(w_list, idx, "0")),
                gabarit_width_flag=_get(gw_flags, idx) in ("on", "true", "1"),
                base_price_eur=_to_decimal(_get(base_prices, idx)),
                surcharge_height_eur=_to_decimal(_get(sur_prices, idx)),
                magnets_price_eur=_to_decimal(_get(magnets_price_eur, idx)),
                magnets_qty=_to_decimal(_get(magnets_qty, idx)),
                cord_pvc_tension_price_eur=_to_decimal(_get(cord_pvc_tension_price_eur, idx)),
                cord_pvc_tension_qty=_to_decimal(_get(cord_pvc_tension_qty, idx)),
                cord_copper_barrel_price_eur=_to_decimal(_get(cord_copper_barrel_price_eur, idx)),
                cord_copper_barrel_qty=_to_decimal(_get(cord_copper_barrel_qty, idx)),
                top_pvc_clip_pair_price_eur=_to_decimal(_get(top_pvc_clip_pair_price_eur, idx)),
                top_pvc_clip_pair_qty=_to_decimal(_get(top_pvc_clip_pair_qty, idx)),
                top_pvc_bar_tape_price_eur_mp=_to_decimal(_get(top_pvc_bar_tape_price_eur_mp, idx)),
                top_pvc_bar_tape_qty=_to_decimal(_get(top_pvc_bar_tape_qty, idx)),
                bottom_wide_bar_price_eur_mp=_to_decimal(_get(bottom_wide_bar_price_eur_mp, idx)),
                bottom_wide_bar_qty=_to_decimal(_get(bottom_wide_bar_qty, idx)),
                top_bar_scotch_price_eur=_to_decimal(_get(top_bar_scotch_price_eur, idx)),
                top_bar_scotch_qty=_to_decimal(_get(top_bar_scotch_qty, idx)),
                metal_cord_fix_price_eur=_to_decimal(_get(metal_cord_fix_price_eur, idx)),
                metal_cord_fix_qty=_to_decimal(_get(metal_cord_fix_qty, idx)),
                
                middle_bracket_price_eur = _to_decimal(_get(middle_bracket_price_eur, idx)),
                middle_bracket_qty = _to_decimal(_get(middle_bracket_qty, idx)),
                remote_15ch_price_eur = _to_decimal(_get(remote_15ch_price_eur, idx)),
                remote_15ch_qty = _to_decimal(_get(remote_15ch_qty, idx)),
                remote_5ch_price_eur = _to_decimal(_get(remote_5ch_price_eur, idx)),
                remote_5ch_qty = _to_decimal(_get(remote_5ch_qty, idx)),
                motor_with_remote_price_eur = _to_decimal(_get(motor_with_remote_price_eur, idx)),
                motor_with_remote_qty = _to_decimal(_get(motor_with_remote_qty, idx)),
                motor_no_remote_price_eur = _to_decimal(_get(motor_no_remote_price_eur, idx)),
                motor_no_remote_qty = _to_decimal(_get(motor_no_remote_qty, idx)),
        
                subtotal_eur=_to_decimal(_get(subtotals, idx)),
                roll_height_info=_get(roll_infos, idx, ""),
                quantity=int(_get(qty_list, idx, "1")),
                control_side=_get(control_sides, idx, "").strip(),
                bottom_fixation=_get(bottom_fixations, idx) in ("on", "true", "1"),
                pvc_plank=_get(pvc_planks, idx) in ("on", "true", "1"),
            )

        messages.success(request, "Замовлення збережено.")
        return redirect("orders:list")

    # -----------------------------------------
    # GET: рендер билдер (создание/редактирование)
    # -----------------------------------------

    # Если новый заказ
    if order is None:
        items_json = "[]"
    else:
        # экспорт Items для JS
        items = []
        for it in order.items.all().order_by("id"):
            items.append({
                "system_sheet": it.system_sheet,
                "table_section": it.table_section,
                "fabric_name": it.fabric_name,
                "fabric_color_code": it.fabric_color_code,
                "height_gabarit_mm": it.height_gabarit_mm,
                "width_fabric_mm": it.width_fabric_mm,
                "gabarit_width_flag": it.gabarit_width_flag,
                "base_price_eur": float(it.base_price_eur),
                "surcharge_height_eur": float(it.surcharge_height_eur),
                
                "magnets_price_eur": float(it.magnets_price_eur),
                "magnets_qty": float(it.magnets_qty),
                "cord_pvc_tension_price_eur": float(it.cord_pvc_tension_price_eur),
                "cord_pvc_tension_qty": float(it.cord_pvc_tension_qty),
                "cord_copper_barrel_price_eur": float(it.cord_copper_barrel_price_eur),
                "cord_copper_barrel_qty": float(it.cord_copper_barrel_qty),
                "top_pvc_clip_pair_price_eur": float(it.top_pvc_clip_pair_price_eur),
                "top_pvc_clip_pair_qty": float(it.top_pvc_clip_pair_qty),
                "top_pvc_bar_tape_price_eur_mp": float(it.top_pvc_bar_tape_price_eur_mp),
                "top_pvc_bar_tape_qty": float(it.top_pvc_bar_tape_qty),
                "bottom_wide_bar_price_eur_mp": float(it.bottom_wide_bar_price_eur_mp),
                "bottom_wide_bar_qty": float(it.bottom_wide_bar_qty),
                "top_bar_scotch_price_eur": float(it.top_bar_scotch_price_eur),
                "top_bar_scotch_qty": float(it.top_bar_scotch_qty),
                "metal_cord_fix_price_eur": float(it.metal_cord_fix_price_eur),
                "metal_cord_fix_qty": float(it.metal_cord_fix_qty),
                
                "middle_bracket_price_eur": float(it.middle_bracket_price_eur),
                "middle_bracket_qty": float(it.middle_bracket_qty),
                "remote_15ch_price_eur": float(it.remote_15ch_price_eur),
                "remote_15ch_qty": float(it.remote_15ch_qty),
                "remote_5ch_price_eur": float(it.remote_5ch_price_eur),
                "remote_5ch_qty": float(it.remote_5ch_qty),
                "motor_with_remote_price_eur": float(it.motor_with_remote_price_eur),
                "motor_with_remote_qty": float(it.motor_with_remote_qty),
                "motor_no_remote_price_eur": float(it.motor_no_remote_price_eur),
                "motor_no_remote_qty": float(it.motor_no_remote_qty),
                
                "subtotal_eur": float(it.subtotal_eur),
                "quantity": it.quantity,
                "roll_height_info": it.roll_height_info,
                "control_side": it.control_side,
                "bottom_fixation": it.bottom_fixation,
                "pvc_plank": it.pvc_plank,
            })
        items_json = json.dumps(items)

    return render(request, "orders/builder.html", {
        "order": order,
        "items_json": items_json,
        "PRICE_SHEET_URL": PRICE_SHEET_URL,
    })
    
    
@login_required
def order_delete(request, pk: int):
    """
    Удаление заказа.
    Customer — может удалить только свой.
    Manager — может удалить любой.
    """
    if is_manager(request.user):
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, customer=request.user)

    if request.method == "POST":
        order.delete()
        messages.success(request, "Замовлення видалено.")
        return redirect("orders:list")

    # GET → страница подтверждения (если хочешь)
    return render(request, "orders/delete_confirm.html", {"order": order})



@login_required
def order_components_builder(request, pk):
    """
    EN: Builder for order components (sheet 'Комплектація').
    UA: Білдер комплектуючих для замовлення (аркуш 'Комплектація').
    """
    order = get_object_or_404(Order, pk=pk)

    # EN: URL to Google Sheets price (Комплектація)
    # UA: URL до Google Sheets прайсу (Комплектація)
    PRICE_SHEET_URL = getattr(settings, "COMPONENTS_PRICE_SHEET_URL", "")

    if request.method == "POST":
        components = parse_components_from_post(request.POST)

        # EN: Replace all existing components with new list
        # UA: Повністю замінюємо поточний список комплектуючих новим
        OrderComponentItem.objects.filter(order=order).delete()

        bulk = []
        for row in components:
            bulk.append(
                OrderComponentItem(
                    order=order,
                    name=row["name"],
                    color=row["color"],
                    unit=row["unit"],
                    price_eur=row["price_eur"],
                    quantity=row["quantity"],
                )
            )

        if bulk:
            OrderComponentItem.objects.bulk_create(bulk)

        messages.success(request, "Комплектуючі для замовлення збережено.")

        # EN: Redirect back to builder or to order detail — adjust as needed
        # UA: Редірект назад у білдер або на сторінку замовлення — за потреби зміни
        return redirect(
            reverse("orders:order_components_builder", kwargs={"pk": order.pk})
        )

    # ---------- GET: формируем components_json для фронта ----------

    # EN: Load existing components for edit mode
    # UA: Завантажуємо існуючі комплектуючі (режим редагування)
    items = (
      order.component_items.all()
      .order_by("id")
    )

    components_payload = []
    for item in items:
        components_payload.append(
            {
                "name": item.name,
                "color": item.color,
                "unit": item.unit,
                "price_eur": str(item.price_eur),
                "quantity": str(item.quantity),
            }
        )

    context = {
        "order": order,
        "PRICE_SHEET_URL": PRICE_SHEET_URL,
        "components_json": json.dumps(components_payload, ensure_ascii=False),
    }

    return render(request, "orders/components_builder.html", context)

