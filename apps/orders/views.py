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
    Customer бачить тільки свої замовлення.
    Manager бачить усі.
    """
    if is_manager(request.user):
        qs = Order.objects.all().order_by("-created_at")
    else:
        qs = Order.objects.filter(customer=request.user).order_by("-created_at")
    return render(request, "orders/list.html", {"orders": qs})

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
        mg_flags = request.POST.getlist("magnets_fixation")

        base_prices = request.POST.getlist("base_price_eur")
        sur_prices = request.POST.getlist("surcharge_height_eur")
        mag_prices = request.POST.getlist("magnets_price_eur")
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
                magnets_fixation=_get(mg_flags, idx) in ("on", "true", "1"),
                base_price_eur=_to_decimal(_get(base_prices, idx)),
                surcharge_height_eur=_to_decimal(_get(sur_prices, idx)),
                magnets_price_eur=_to_decimal(_get(mag_prices, idx)),
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
                "magnets_fixation": it.magnets_fixation,
                "base_price_eur": float(it.base_price_eur),
                "surcharge_height_eur": float(it.surcharge_height_eur),
                "magnets_price_eur": float(it.magnets_price_eur),
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

