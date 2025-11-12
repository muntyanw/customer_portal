# apps/orders/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Order
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
