# apps/orders/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.db import transaction
from django.db.models import Case, DecimalField, ExpressionWrapper, F, Sum, When, Max
from django.db.models.functions import Coalesce
from django.contrib import messages
from .models import (
    Order,
    OrderItem,
    Transaction,
    OrderStatusLog,
    NotificationEmail,
    PaymentMessage,
    OrderComponentItem,
    CurrencyRate,
)
from apps.accounts.roles import is_manager
import json
from decimal import Decimal, InvalidOperation
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.core.files.base import ContentFile
from io import BytesIO
from openpyxl import Workbook
from django.utils import timezone
import datetime
from .utils_components import parse_components_from_post
from django.urls import reverse
from .services_currency import get_current_eur_rate, update_eur_rate_from_nbu
from django.views.decorators.http import require_POST
        
        
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


def _orders_scope(user):
    if is_manager(user):
        return Order.objects.all()
    return Order.objects.filter(customer=user)


def _transactions_scope(user):
    if is_manager(user):
        return Transaction.objects.select_related("customer", "customer__customerprofile", "created_by", "order")
    return Transaction.objects.select_related("customer", "customer__customerprofile", "created_by", "order").filter(customer=user)

def _order_rate(order, current_rate: Decimal) -> Decimal:
    """
    Pick rate: frozen for робота+, або поточний для прорахунку.
    """
    if order.status != Order.STATUS_QUOTE and order.eur_rate:
        return Decimal(order.eur_rate)
    return Decimal(current_rate or 0)


def _order_base_total(order) -> Decimal:
    """
    Return stored total (без націнки). Якщо відсутнє/нульове, рахуємо по items.
    """
    stored = Decimal(order.total_eur or 0)
    if stored > 0:
        return stored
    agg = order.items.annotate(
        line_total=ExpressionWrapper(
            F("subtotal_eur") * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    ).aggregate(total=Sum("line_total")).get("total") or Decimal("0")
    return agg

STATUS_LABELS = dict(Order.STATUS_CHOICES)


def _set_order_totals_uah(orders, current_rate: Decimal):
    """Attach total_uah_display/display_rate to orders for templates."""
    for o in orders:
        rate = _order_rate(o, current_rate)
        total_eur = _order_base_total(o)
        o.display_rate = rate
        o.total_uah_display = (total_eur * rate).quantize(Decimal("0.01"))
    return orders


def _order_total_uah(order, current_rate: Decimal) -> Decimal:
    return (_order_base_total(order) * _order_rate(order, current_rate)).quantize(Decimal("0.01"))


def _get_payment_message_text():
    return (
        PaymentMessage.objects.filter(is_active=True)
        .order_by("-created_at")
        .values_list("text", flat=True)
        .first()
    )


def _payment_shortage_context(order):
    """Return dict with shortage and list of orders covering it (for prompt)."""
    if not order:
        return None
    current_rate = get_current_eur_rate()
    order_total_uah = _order_total_uah(order, current_rate)
    balance = compute_balance(order.customer)
    shortage = Decimal(balance or 0) - order_total_uah
    if shortage >= 0:
        return None
    shortage = shortage * -1

    cover_orders = []
    cover_total = Decimal("0")
    existing_orders = (
        _orders_scope(order.customer)
        .filter(status__in=[Order.STATUS_IN_WORK, Order.STATUS_READY, Order.STATUS_SHIPPED])
        .exclude(pk=order.pk)
        .order_by("-created_at")
    )
    for o in existing_orders:
        cover_total += _order_total_uah(o, current_rate)
        cover_orders.append(o.pk)
        if cover_total >= shortage:
            break

    return {
        "shortage": shortage.quantize(Decimal("0.01")),
        "orders": cover_orders,
    }


def _build_order_workbook(order):
    """Generate Excel workbook for order (формат схожий на 'Приклад.xls') and attach to instance."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Счет"
    profile = getattr(order.customer, "customerprofile", None)
    rate = Decimal(order.eur_rate or get_current_eur_rate() or 0)

    header_lines = [
        ["", "Віконні системи Wenster, www.oknaeuro.kiev.ua", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["", "(063) 377-85-46; (068) 352-49-09 (viber); (095) 308-09-96", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
    ]
    for line in header_lines:
        ws.append(line)

    created_str = order.created_at.astimezone(timezone.get_current_timezone()).strftime("%d.%m.%y") if order.created_at else ""
    customer_line = f"{created_str} замовлення № {order.pk or ''} клієнт: {getattr(profile, 'full_name', '') or order.customer}"
    ws.append([customer_line, "", "", "", "", "", "", "", ""])

    ws.append(["Система", "Тканина", "Ширина", "Висота", "Управління", "Нижня фіксація", "Кількість", "Вартість", "Примітка"])

    def price_uah(subtotal_eur, qty):
        return float((Decimal(subtotal_eur or 0) * Decimal(qty or 0) * rate).quantize(Decimal("0.01"))) if rate else float(Decimal(subtotal_eur or 0) * Decimal(qty or 0))

    total_uah = Decimal("0")

    for it in order.items.all():
        qty = it.quantity
        total_row = price_uah(it.subtotal_eur, qty)
        total_uah += Decimal(str(total_row or 0))
        ws.append([
            it.system_sheet,
            it.fabric_name,
            it.width_fabric_mm,
            it.height_gabarit_mm,
            it.control_side,
            "Так" if it.bottom_fixation else "",
            qty,
            total_row,
            it.roll_height_info or "",
        ])

    for it in order.component_items.all():
        qty = it.quantity
        total_row = price_uah(it.price_eur, qty)
        total_uah += Decimal(str(total_row or 0))
        ws.append([
            f"Комплектуюча: {it.name}",
            it.color,
            "",
            "",
            "",
            "",
            qty,
            total_row,
            it.unit,
        ])

    total_display = float(total_uah.quantize(Decimal("0.01"))) if total_uah else ""
    ws.append([f"Примітки: {order.note or ''}", "", "", "", "", "", "Всього, грн", total_display, ""])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"order_{order.pk}.xlsx"
    order.workbook_file.save(filename, ContentFile(buffer.getvalue()), save=False)
    return filename, buffer.getvalue()


def _send_order_in_work_email(order, request, workbook_payload=None):
    """Send notification to configured recipients when an order enters 'in work'."""
    recipients = list(
        NotificationEmail.objects.filter(is_active=True).values_list("email", flat=True)
    )
    if not recipients:
        return

    profile = getattr(order.customer, "customerprofile", None)
    full_name = getattr(profile, "full_name", "") or ""
    phone = getattr(profile, "phone", "") or ""

    try:
        order_url = request.build_absolute_uri(reverse("orders:builder_edit", args=[order.pk]))
    except Exception:
        order_url = ""

    subject = f"Замовлення #{order.pk} відправлено в роботу"
    body_lines = [
        f"Замовлення #{order.pk} відправлено в роботу.",
        f"Клієнт: {order.customer}",
    ]
    if full_name:
        body_lines.append(f"ПІБ: {full_name}")
    if phone:
        body_lines.append(f"Телефон: {phone}")
    total_uah = getattr(order, "total_uah_display", "")
    if not total_uah:
        try:
            total_uah = (Decimal(order.total_eur or 0) * Decimal(order.eur_rate or 0)).quantize(Decimal("0.01"))
        except Exception:
            total_uah = ""
    if total_uah != "":
        body_lines.append(f"Сума (UAH): {total_uah}")
    if order_url:
        body_lines.append(f"Посилання: {order_url}")

    email = EmailMessage(
        subject=subject,
        body="\n".join(body_lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )

    filename = None
    data = None
    if workbook_payload:
        filename, data = workbook_payload
    elif order.workbook_file:
        try:
            with order.workbook_file.open("rb") as f:
                data = f.read()
                filename = order.workbook_file.name.split("/")[-1]
        except Exception:
            data = None
    if filename and data:
        email.attach(filename, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    email.send(fail_silently=True)


def _prepare_to_work(order, request):
    """Set rates for quote->work and block if credit not allowed."""
    if order.status != Order.STATUS_QUOTE:
        return True

    current_rate = get_current_eur_rate()
    order.eur_rate = current_rate
    order.eur_rate_at_creation = current_rate
    order.save(update_fields=["eur_rate", "eur_rate_at_creation"])

    balance_before = compute_balance(order.customer)
    projected_balance = balance_before - order.total_eur
    shortage = projected_balance * -1 if projected_balance < 0 else Decimal("0")
    profile = getattr(order.customer, "customerprofile", None)
    credit_allowed = getattr(profile, "credit_allowed", False)
    if shortage > 0 and not credit_allowed:
        messages.warning(
            request,
            f"Оплатіть суму {shortage} для відправки в роботу.",
        )
        return False
    return True


def _apply_status_change(order, new_status, request):
    """Shared status transition logic for rollers & components."""
    if not new_status or new_status == order.status:
        return True

    workbook_payload = None
    if new_status == Order.STATUS_IN_WORK:
        if not _prepare_to_work(order, request):
            return False
        workbook_payload = _build_order_workbook(order)
        order.status = new_status
        order.save(update_fields=["status", "workbook_file"])
        OrderStatusLog.objects.create(
            order=order,
            status=new_status,
            user=request.user,
        )
        _send_order_in_work_email(order, request, workbook_payload)
        return True

    order.status = new_status
    order.save(update_fields=["status"])
    OrderStatusLog.objects.create(
        order=order,
        status=new_status,
        user=request.user,
    )
    return True


def compute_balance(user):
    current_rate = get_current_eur_rate()
    orders_qs = _orders_scope(user).filter(
        status__in=[
            Order.STATUS_IN_WORK,
            Order.STATUS_READY,
            Order.STATUS_SHIPPED,
        ]
    )
    orders_sum_uah = sum(
        (_order_base_total(o) * _order_rate(o, current_rate)).quantize(Decimal("0.01"))
        for o in orders_qs
    )

    tx_qs = _transactions_scope(user)
    tx_total_uah = tx_qs.aggregate(
        total=Sum(
            Case(
                When(
                    type=Transaction.DEBIT,
                    then=ExpressionWrapper(
                        F("amount") * F("eur_rate"),
                        output_field=DecimalField(max_digits=18, decimal_places=4),
                    ),
                ),
                default=ExpressionWrapper(
                    -F("amount") * F("eur_rate"),
                    output_field=DecimalField(max_digits=18, decimal_places=4),
                ),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            )
        )
    )["total"] or Decimal("0")
    tx_total_uah = Decimal(tx_total_uah).quantize(Decimal("0.01"))

    return tx_total_uah - orders_sum_uah


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["customer", "type", "amount", "description", "order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_rate = get_current_eur_rate()
        rate_decimal = Decimal(self.current_rate or 0)
        self.current_rate = rate_decimal.quantize(Decimal("0.0001")) if rate_decimal else rate_decimal
        User = get_user_model()
        self.fields["customer"].queryset = (
            User.objects.select_related("customerprofile")
            .order_by("customerprofile__full_name", "email")
        )

        def _label(u):
            profile = getattr(u, "customerprofile", None)
            full_name = getattr(profile, "full_name", "") or u.get_full_name() or u.username
            phone = getattr(profile, "phone", "") or ""
            contact_email = getattr(profile, "contact_email", "") or u.email
            parts = [full_name]
            if phone:
                parts.append(phone)
            if contact_email:
                parts.append(contact_email)
            return " · ".join(parts)

        self.fields["customer"].label_from_instance = _label
        self.fields["customer"].widget.attrs.update({"class": "form-select", "data-customer-picker": "true"})
        self.fields["type"].widget.attrs.update({"class": "form-select"})
        self.fields["order"].widget.attrs.update({"class": "form-select"})
        self.fields["amount"].label = "Сума, грн"
        self.fields["amount"].widget.attrs.update(
            {"class": "form-control", "step": "0.01", "min": "0", "inputmode": "decimal"}
        )
        self.fields["description"].widget.attrs.update({"class": "form-control"})

    def clean_amount(self):
        amount_uah = self.cleaned_data.get("amount") or Decimal("0")
        rate = Decimal(self.current_rate or 0)
        if rate <= 0:
            raise forms.ValidationError("Немає актуального курсу EUR для конвертації.")
        return (amount_uah / rate).quantize(Decimal("0.00001"))

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.eur_rate = Decimal(self.current_rate or 0)
        if commit:
            obj.save()
        return obj

@login_required
def order_list(request):
    """
    EN: List of roller orders (with positions).
    UA: Список замовлень з тканинними ролетами.
    """
    User = get_user_model()
    status_filter = request.GET.get("status") or ""
    customer_filter = request.GET.get("customer") or ""
    orders_qs = (
        _orders_scope(request.user)
        .select_related("customer", "customer__customerprofile")
        .annotate(last_status_at=Coalesce(Max("status_logs__created_at"), "created_at"))
        .prefetch_related("status_logs")
        .exclude(component_items__isnull=False)  # exclude component orders from rollers list
        .order_by("-last_status_at", "-created_at")
        .distinct()
    )

    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    if customer_filter and is_manager(request.user):
        orders_qs = orders_qs.filter(customer_id=customer_filter)

    customers_filter_list = (
        User.objects.filter(orders__isnull=False).select_related("customerprofile").distinct()
        if is_manager(request.user) else []
    )
    current_rate = get_current_eur_rate()
    orders_qs = _set_order_totals_uah(orders_qs, current_rate)

    context = {
        "orders": orders_qs,
        "statuses": Order.STATUS_CHOICES,
        "status_filter": status_filter,
        "customer_filter": customer_filter,
        "customer_options": customers_filter_list,
        "list_mode": "rollers",
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_components_list(request):
    """
    EN: List of orders that have components.
    UA: Список замовлень, у яких є комплектуючі.
    """
    User = get_user_model()
    status_filter = request.GET.get("status") or ""
    customer_filter = request.GET.get("customer") or ""

    qs = (
        _orders_scope(request.user)
        .select_related("customer", "customer__customerprofile")
        .annotate(last_status_at=Coalesce(Max("status_logs__created_at"), "created_at"))
        .prefetch_related("status_logs")
        .filter(component_items__isnull=False)
        .distinct()
        .order_by("-last_status_at", "-created_at")
    )

    if status_filter:
        qs = qs.filter(status=status_filter)
    if customer_filter and is_manager(request.user):
        qs = qs.filter(customer_id=customer_filter)

    customers_filter_list = (
        User.objects.filter(orders__isnull=False).select_related("customerprofile").distinct()
        if is_manager(request.user) else []
    )
    current_rate = get_current_eur_rate()
    qs = _set_order_totals_uah(qs, current_rate)

    context = {
        "orders": qs,
        "list_mode": "components",
        "statuses": Order.STATUS_CHOICES,
        "status_filter": status_filter,
        "customer_filter": customer_filter,
        "customer_options": customers_filter_list,
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_notifications_settings(request):
    """
    EN: Manage recipient emails for order-in-work notifications.
    UA: Керування email-адресами для сповіщень про відправку замовлення в роботу.
    """
    if not is_manager(request.user):
        messages.error(request, "Доступно лише менеджерам.")
        return redirect("orders:list")

    EmailFormSet = forms.modelformset_factory(
        NotificationEmail,
        fields=["email", "is_active"],
        extra=1,
        can_delete=True,
        widgets={
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        },
    )
    PaymentFormSet = forms.modelformset_factory(
        PaymentMessage,
        fields=["text", "is_active"],
        extra=1,
        can_delete=True,
        widgets={
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Текст повідомлення"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        },
    )

    emails_qs = NotificationEmail.objects.order_by("email")
    payments_qs = PaymentMessage.objects.order_by("-created_at")

    if request.method == "POST":
        email_formset = EmailFormSet(request.POST, queryset=emails_qs, prefix="emails")
        payment_formset = PaymentFormSet(request.POST, queryset=payments_qs, prefix="payments")
        if email_formset.is_valid() and payment_formset.is_valid():
            email_formset.save()
            payment_formset.save()
            messages.success(request, "Налаштування збережено.")
            return redirect("orders:notifications_settings")
    else:
        email_formset = EmailFormSet(queryset=emails_qs, prefix="emails")
        payment_formset = PaymentFormSet(queryset=payments_qs, prefix="payments")

    return render(
        request,
        "orders/notification_settings.html",
        {
            "email_formset": email_formset,
            "payment_formset": payment_formset,
        },
    )


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

    readonly = bool(order and (not is_manager(request.user) and order.status != Order.STATUS_QUOTE))

    # -------------------------------------
    # POST: создание или обновление
    # -------------------------------------
    if request.method == "POST":
        if readonly:
            messages.warning(request, "Це замовлення можна лише переглядати.")
            return redirect("orders:builder_edit", pk=order.pk)
        action = request.POST.get("status_action") or "save"
        # Если ордера нет — создаём
        if order is None:
            markup_percent = _to_decimal(request.POST.get("markup_percent"), default="0")
            current_rate = get_current_eur_rate()
            order = Order.objects.create(
                customer=request.user,
                eur_rate_at_creation=current_rate,
                eur_rate=current_rate,
                markup_percent=markup_percent,
                status=Order.STATUS_QUOTE,
            )
        order.note = (request.POST.get("note") or "").strip()

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
        GbDiffWidthMm = request.POST.getlist("GbDiffWidthMm")
        gb_width_mm = request.POST.getlist("gb_width_mm")

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
        top_bar_scotch_price_eur_mp = request.POST.getlist("top_bar_scotch_price_eur_mp")
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
        metal_kronsht_price_eur = request.POST.getlist("metal_kronsht_price_eur")
        metal_kronsht_qty = request.POST.getlist("metal_kronsht_qty")
        
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
                gb_width_mm=_to_decimal(_get(gb_width_mm, idx)),
                GbDiffWidthMm=_to_decimal(_get(GbDiffWidthMm, idx)),
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
                top_bar_scotch_price_eur_mp=_to_decimal(_get(top_bar_scotch_price_eur_mp, idx)),
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
                metal_kronsht_price_eur = _to_decimal(_get(metal_kronsht_price_eur, idx)),
                metal_kronsht_qty = _to_decimal(_get(metal_kronsht_qty, idx)),
        
                subtotal_eur=_to_decimal(_get(subtotals, idx)),
                roll_height_info=_get(roll_infos, idx, ""),
                quantity=int(_get(qty_list, idx, "1")),
                control_side=_get(control_sides, idx, "").strip(),
                bottom_fixation=_get(bottom_fixations, idx) in ("on", "true", "1"),
                pvc_plank=_get(pvc_planks, idx) in ("on", "true", "1"),
            )

        markup_percent = _to_decimal(request.POST.get("markup_percent"), default=str(order.markup_percent or "0"))
        eur_rate_value = _to_decimal(
            request.POST.get("eur_rate"),
            default=str(order.eur_rate or get_current_eur_rate()),
        )

        items_total = (
            order.items.annotate(
                line_total=ExpressionWrapper(
                    F("subtotal_eur") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
            .aggregate(total=Sum("line_total"))
            .get("total")
            or Decimal("0")
        )

        total_with_markup = items_total * (Decimal("1") + markup_percent / Decimal("100"))

        order.markup_percent = markup_percent.quantize(Decimal("0.01"))
        order.eur_rate = eur_rate_value
        if not order.eur_rate_at_creation:
            order.eur_rate_at_creation = eur_rate_value
        order.total_eur = items_total.quantize(Decimal("0.01"))
        order.save(update_fields=["markup_percent", "eur_rate", "total_eur", "eur_rate_at_creation", "note"])

        new_status = order.status
        if action == "to_work":
            new_status = Order.STATUS_IN_WORK
        elif action == "next" and is_manager(request.user):
            new_status = order.next_status() or order.status
        elif action == "prev" and is_manager(request.user):
            new_status = order.prev_status() or order.status

        if new_status and not _apply_status_change(order, new_status, request):
            return redirect("orders:builder_edit", pk=order.pk)

        messages.success(request, "Замовлення збережено.")
        return redirect("orders:list")

    # -----------------------------------------
    # GET: рендер билдер (создание/редактирование)
    # -----------------------------------------

    # Если новый заказ
    if order is None:
        items_json = "[]"
        next_status_label = STATUS_LABELS.get(Order.STATUS_IN_WORK)
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
                "GbDiffWidthMm": float(it.GbDiffWidthMm),
                "gb_width_mm": float(it.gb_width_mm),
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
                "top_bar_scotch_price_eur_mp": float(it.top_bar_scotch_price_eur_mp),
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
                "metal_kronsht_price_eur": float(it.metal_kronsht_price_eur),
                "metal_kronsht_qty": float(it.metal_kronsht_qty),
                
                "subtotal_eur": float(it.subtotal_eur),
                "quantity": it.quantity,
                "roll_height_info": it.roll_height_info,
                "control_side": it.control_side,
                "bottom_fixation": it.bottom_fixation,
                "pvc_plank": it.pvc_plank,
            })
        items_json = json.dumps(items)
        next_code = order.next_status()
        next_status_label = STATUS_LABELS.get(next_code) if next_code else None

    status_logs = order.status_logs.all() if order else []

    builder_rate = get_current_eur_rate()
    if order and order.status != Order.STATUS_QUOTE and order.eur_rate:
        builder_rate = order.eur_rate

    shortage_ctx = _payment_shortage_context(order)

    return render(request, "orders/builder.html", {
        "order": order,
        "items_json": items_json,
        "PRICE_SHEET_URL": PRICE_SHEET_URL,
        "status_logs": status_logs,
        "eur_rate": builder_rate,
        "next_status_label": next_status_label,
        "readonly": readonly,
        "payment_message_text": _get_payment_message_text(),
        "payment_shortage": shortage_ctx,
    })
    
    
@login_required
def order_delete(request, pk: int):
    """
    Удаление заказа.
    Customer — может удалить только свой.
    Manager — может удалить любой.
    """
    redirect_target = "orders:list"
    if is_manager(request.user):
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, customer=request.user)

    # если есть комплектующие, возвращаем на список комплектующих
    if order.component_items.exists():
        redirect_target = "orders:components_list"

    if request.method == "POST":
        order.delete()
        messages.success(request, "Замовлення видалено.")
        return redirect(redirect_target)

    # GET → страница подтверждения (если хочешь)
    return render(request, "orders/delete_confirm.html", {"order": order})


@login_required
def transaction_create(request):
    if not is_manager(request.user):
        messages.error(request, "Створювати транзакції може лише менеджер.")
        return redirect("orders:list")

    current_rate = get_current_eur_rate()
    if Decimal(current_rate or 0) <= 0:
        messages.warning(request, "Немає актуального курсу EUR. Оновіть курс перед створенням транзакції.")

    initial = {}
    if "customer" in request.GET:
        initial["customer"] = request.GET.get("customer")

    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.created_by = request.user
            tx.save()
            messages.success(request, "Транзакцію створено.")
            return redirect("orders:balances")
    else:
        form = TransactionForm(initial=initial)

    return render(request, "orders/transaction_form.html", {"form": form, "current_rate": current_rate})


@login_required
def balances_history(request):
    """
    EN: Orders + transactions timeline with balance and filters.
    UA: Історія замовлень і транзакцій з фільтрами.
    """
    User = get_user_model()
    status_filter = request.GET.get("status") or ""
    customer_filter = request.GET.get("customer") or ""
    type_filter = request.GET.get("type") or ""
    balance_user = request.user

    orders_qs = (
        _orders_scope(request.user)
        .select_related("customer", "customer__customerprofile")
        .prefetch_related("status_logs", "component_items")
        .exclude(status=Order.STATUS_QUOTE)  # Прорахунок не впливає на баланс
        .order_by("-created_at")
    )
    tx_qs = _transactions_scope(request.user).order_by("-created_at")

    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
    if type_filter == "orders":
        tx_qs = tx_qs.none()
    elif type_filter == "transactions":
        orders_qs = orders_qs.none()

    if customer_filter and is_manager(request.user):
        balance_user = get_object_or_404(User, pk=customer_filter)
        orders_qs = orders_qs.filter(customer=balance_user)
        tx_qs = tx_qs.filter(customer=balance_user)

    current_rate = get_current_eur_rate()
    orders_qs = _set_order_totals_uah(orders_qs, current_rate)

    events = []
    for o in orders_qs:
        events.append({"type": "order", "created_at": o.created_at, "object": o})
    for tx in tx_qs:
        events.append({"type": "transaction", "created_at": tx.created_at, "object": tx})
    events.sort(key=lambda x: x["created_at"], reverse=True)

    customers_filter_list = (
        User.objects.filter(orders__isnull=False).select_related("customerprofile").distinct()
        if is_manager(request.user) else []
    )

    context = {
        "events": events,
        "statuses": Order.STATUS_CHOICES,
        "status_filter": status_filter,
        "customer_filter": customer_filter,
        "type_filter": type_filter,
        "customer_options": customers_filter_list,
        "balance": compute_balance(balance_user),
        "balance_user": balance_user,
        # Ensure header balance reflects filtered customer (for managers)
        "user_balance": compute_balance(balance_user),
    }
    return render(request, "orders/balances_history.html", context)



@login_required
def order_components_builder(request, pk):
    """
    EN: Builder for order components (sheet 'Комплектація').
    UA: Білдер комплектуючих для замовлення (аркуш 'Комплектація').
    """
    order = get_object_or_404(Order, pk=pk)
    readonly = bool(order and (not is_manager(request.user) and order.status != Order.STATUS_QUOTE))

    if request.method == "POST":
        if readonly:
            messages.warning(request, "Це замовлення можна лише переглядати.")
            return redirect("orders:order_components_builder", pk=order.pk)

        action = request.POST.get("status_action") or "save"
        components = parse_components_from_post(request.POST)

        # EN: Replace all existing components with new list
        # UA: Повністю замінюємо поточний список комплектуючих новим
        OrderComponentItem.objects.filter(order=order).delete()

        total_eur = Decimal("0")
        bulk = []
        for row in components:
            total_eur += Decimal(row["price_eur"] or 0) * Decimal(row["quantity"] or 0)
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
        # Save total for order (used in listings/balance)
        order.total_eur = total_eur
        order.eur_rate = order.eur_rate or get_current_eur_rate()

        # Status transitions (mirror roller orders)
        new_status = None
        if action == "to_work":
            new_status = Order.STATUS_IN_WORK
        elif action == "next":
            new_status = order.next_status()
        elif action == "prev":
            new_status = order.prev_status()
        # Default save keeps current status

        order.save(update_fields=["total_eur", "eur_rate"])

        if new_status and not _apply_status_change(order, new_status, request):
            return redirect(reverse("orders:order_components_builder", kwargs={"pk": order.pk}))

        messages.success(request, "Замовлення збережено.")

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
        "status_logs": order.status_logs.all(),
        "readonly": readonly,
        "next_status_label": STATUS_LABELS.get(order.next_status()) if order else None,
        "eur_rate": order.eur_rate or get_current_eur_rate(),
        "payment_message_text": _get_payment_message_text(),
        "payment_shortage": _payment_shortage_context(order),
    }

    return render(request, "orders/components_builder.html", context)


@login_required
def order_components_builder_new(request):
    """
    EN: Create new order and go to components builder.
    UA: Створює нове замовлення і переходить у білдер комплектуючих.
    """
    order = Order.objects.create(
        customer=request.user,        # ✔ обязателен, иначе IntegrityError по customer_id
        title="Замовлення (комплектуючі)",  # любой не пустой заголовок
        description="",
        status=Order.STATUS_QUOTE,
        eur_rate_at_creation=get_current_eur_rate(),
        eur_rate=get_current_eur_rate(),
        markup_percent=Decimal("0"),
        total_eur=Decimal("0"),
    )
    return redirect("orders:order_components_builder", pk=order.pk)


@staff_member_required  # EN: only staff can update; UA: тільки staff-користувачі можуть оновлювати
@require_POST
def update_eur_rate_view(request):
    """
    EN: Update EUR rate from NBU and redirect back.
    UA: Оновлює курс EUR з НБУ та повертає назад.
    """
    mode = request.POST.get("mode") or "online"
    if mode == "manual":
        rate = request.POST.get("rate")
        try:
            rate_val = Decimal(str(rate).replace(",", "."))
            if rate_val <= 0:
                raise InvalidOperation
            obj, _ = CurrencyRate.objects.update_or_create(
                currency="EUR",
                defaults={"rate_uah": rate_val, "source": "manual"},
            )
            messages.success(
                request,
                f"Курс EUR збережено вручну: {obj.rate_uah} грн",
            )
        except Exception:
            messages.error(request, "Введіть коректний курс EUR (приклад: 39.50)")
    else:
        try:
            obj = update_eur_rate_from_nbu()
            messages.success(
                request,
                f"Курс EUR оновлено: {obj.rate_uah} грн (джерело: {obj.source})"
            )
        except Exception as e:
            messages.error(
                request,
                f"Не вдалося оновити курс EUR: {e}"
            )

    # EN: redirect back where user came from; UA: повертаємось туди, звідки прийшли
    next_url = request.META.get("HTTP_REFERER") or reverse("core:dashboard")
    return redirect(next_url)
