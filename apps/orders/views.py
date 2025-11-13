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
    UA: Сторінка для складання замовлення: динамічні рядки (OrderItem) + автоперерахунок через API.
    EN: Order builder page with dynamic rows.
    """
    if request.method == "POST":
        # Create order and its items from POST arrays
        order = Order.objects.create(customer=request.user)
        # Можна зберегти organization через профіль
        profile = getattr(request.user, "customerprofile", None)
        org = getattr(profile, "organization", None)

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
        )
        for row in rows:
            ss, ts, fab, hg, wf, gw, mg, bp, sc, mp, sub, rollinfo, qty = row
            item = OrderItem(
                order=order, organization=org,
                system_sheet=ss, table_section=ts, fabric_name=fab,
                height_gabarit_mm=int(hg or 0),
                width_fabric_mm=int(wf or 0),
                gabarit_width_flag=(gw == "on"),
                magnets_fixation=(mg == "on"),
                base_price_eur=bp or 0,
                surcharge_height_eur=sc or 0,
                magnets_price_eur=mp or 0,
                subtotal_eur=sub or 0,
                roll_height_info=rollinfo or "",
                quantity=int(qty or 1),
            )
            item.save()

        messages.success(request, "Замовлення створено.")
        return redirect("orders:list")

    return render(request, "orders/builder.html", {
        "PRICE_SHEET_URL": PRICE_SHEET_URL
    })
