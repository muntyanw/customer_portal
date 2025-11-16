# apps/orders/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.db import transaction
from django.contrib import messages
from .models import Order, OrderItem
from .forms import OrderItemForm
from apps.accounts.roles import is_manager

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["title", "description", "attachment"]

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
    """
    Customer може дивитись лише свої замовлення.
    Manager — будь-які.
    """
    if is_manager(request.user):
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/detail.html", {"order": order})

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
def order_builder(request):
    """
    UA: Сторінка для складання замовлення: динамічні позиції (OrderItem) + автоперерахунок через API.
    EN: Order builder page with dynamic rows and live price preview.
    """
    if request.method == "POST":
        # 1) створюємо замовлення (тільки customer, title/description можна буде додавати окремо)
        order = Order.objects.create(customer=request.user)

        # optional: organization from profile
        profile = getattr(request.user, "customerprofile", None)
        org = getattr(profile, "organization", None)

        # 2) зчитуємо масиви з форми
        rows = zip(
            request.POST.getlist("system_sheet"),
            request.POST.getlist("table_section"),
            request.POST.getlist("fabric_name"),
            request.POST.getlist("height_gabarit_mm"),
            request.POST.getlist("width_fabric_mm"),
            request.POST.getlist("gabarit_width_flag"),
            request.POST.getlist("magnets_fixation"),
            request.POST.getlist("base_price_eur"),
            request.POST.getlist("surcharge_height_eur"),
            request.POST.getlist("magnets_price_eur"),
            request.POST.getlist("subtotal_eur"),
            request.POST.getlist("roll_height_info"),
            request.POST.getlist("quantity"),
            request.POST.getlist("control_side"),
            request.POST.getlist("bottom_fixation"),
            request.POST.getlist("pvc_plank"),
        )

        for row in rows:
            (
                system_sheet,
                table_section,
                fabric_name,
                h_gab,
                w_fab,
                gw_flag,
                mg_flag,
                base_price,
                sur_price,
                mag_price,
                subtotal,
                rollinfo,
                qty,
                control_side,
                bottom_fixation,
                pvc_plank,
            ) = row

            item = OrderItem(
                order=order,
                organization=org,
                system_sheet=system_sheet or "",
                table_section=table_section or "",
                fabric_name=fabric_name or "",
                height_gabarit_mm=int(h_gab or 0),
                width_fabric_mm=int(w_fab or 0),
                gabarit_width_flag=(gw_flag == "on"),
                magnets_fixation=(mg_flag == "on"),
                base_price_eur=base_price or 0,
                surcharge_height_eur=sur_price or 0,
                magnets_price_eur=mag_price or 0,
                subtotal_eur=subtotal or 0,
                roll_height_info=rollinfo or "",
                quantity=int(qty or 1),
                control_side=(control_side or "").strip(),
                bottom_fixation=(bottom_fixation == "on"),
                pvc_plank=(pvc_plank == "on"),
            )
            item.save()

        messages.success(request, "Замовлення створено.")
        return redirect("orders:list")

    # GET
    return render(
        request,
        "orders/builder.html",
        {
            "PRICE_SHEET_URL": PRICE_SHEET_URL,
        },
    )