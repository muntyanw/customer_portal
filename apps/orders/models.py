#apps/orders/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

class Order(models.Model):
    STATUS_QUOTE = "quote"  # Прорахунок / чернетка
    STATUS_IN_WORK = "in_work"  # В роботі
    STATUS_READY = "ready_for_pickup"  # Готовий до вивозу
    STATUS_SHIPPED = "shipped"  # Відвантажено

    STATUS_CHOICES = [
        (STATUS_QUOTE, "Прорахунок"),
        (STATUS_IN_WORK, "В роботі"),
        (STATUS_READY, "Готовий до вивозу"),
        (STATUS_SHIPPED, "Відвантажено"),
    ]

    STATUS_FLOW = [
        STATUS_QUOTE,
        STATUS_IN_WORK,
        STATUS_READY,
        STATUS_SHIPPED,
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUOTE)
    attachment = models.FileField(upload_to="attachments/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NEW: курс EUR на момент створення замовлення
    eur_rate_at_creation = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Курс EUR/UAH на момент створення замовлення",
    )

    total_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Підсумкова сума замовлення в EUR (з націнкою)",
    )
    note = models.TextField(blank=True, verbose_name="Примітка")

    eur_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Курс EUR/UAH, що застосовано для цього замовлення",
    )

    markup_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Процент націнки, що застосовано до замовлення",
    )
    workbook_file = models.FileField(upload_to="order_exports/", blank=True, null=True)

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def next_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        if idx < len(self.STATUS_FLOW) - 1:
            return self.STATUS_FLOW[idx + 1]
        return None

    def prev_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        if idx > 0:
            return self.STATUS_FLOW[idx - 1]
        return None
    
    
from django.db import models


class OrderItem(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="items")
    organization = models.ForeignKey(
        "customers.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    # Selects
    system_sheet = models.CharField(max_length=128)      # назва вкладки (система)
    table_section = models.CharField(max_length=256)     # заголовок секції (колір системи)
    fabric_name = models.CharField(max_length=128)       # назва тканини

    fabric_color_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Код кольору тканини",
    )

    # Numeric input
    height_gabarit_mm = models.PositiveIntegerField()    # габаритна висота, мм
    width_fabric_mm = models.PositiveIntegerField()      # введена ширина, мм (зараз = по тканині; логіку можна змінити пізніше)
    GbDiffWidthMm = models.PositiveIntegerField(default=0)      
    gb_width_mm = models.PositiveIntegerField(default=0)      

    # Info
    roll_height_info = models.CharField(
        max_length=64,
        blank=True,
        help_text="Текстова підказка типу 'Висота рулону, мм'",
    )

    # Flags / options (basic)
    gabarit_width_flag = models.BooleanField(default=False)
    bottom_fixation = models.BooleanField(default=False)
    pvc_plank = models.BooleanField(default=False)

    # Control side
    control_side = models.CharField(
        max_length=32,
        blank=True,
        help_text="Сторона керування (лівий/правий ланцюжок тощо)",
    )

    # Base prices (EUR) for main product
    base_price_eur = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    surcharge_height_eur = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    magnets_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість магнітної фіксації",
    )
    
    magnets_price_eur = models.DecimalField(  # можна залишити як 'total' або перепризначити під одиничну ціну
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна магнітної фіксації (може бути загальною або одиничною, залежно від логіки калькулятора)",
    )
    subtotal_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Проміжна сума по позиції (без множення на quantity)",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Кількість однакових виробів у цій позиції",
    )

    # ---------------------------------------------------------------------
    # Extra options / accessories (per piece or per meter)
    # ---------------------------------------------------------------------
    # 1) Фіксація Леска ПВХ з дотяжкою (шт)
    cord_pvc_tension_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість фіксацій лески ПВХ з дотяжкою, шт",
    )
    cord_pvc_tension_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна за одну фіксацію лески ПВХ з дотяжкою, EUR/шт",
    )

    # 2) Фіксація Леска з мідною діжкою (шт)
    cord_copper_barrel_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість фіксацій лески з мідною діжкою, шт",
    )
    cord_copper_barrel_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна за одну фіксацію лески з мідною діжкою, EUR/шт",
    )

    # 3) Фіксація Магніт (шт)
    magnet_fix_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість магнітних фіксацій, шт",
    )
    magnet_fix_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна за одну магнітну фіксацію, EUR/шт",
    )

    # 4) Кліпса кріплення для верхньої планки ПВХ, пара (шт = пар)
    top_pvc_clip_pair_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість кліпс для верхньої планки ПВХ, пар",
    )
    top_pvc_clip_pair_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна за одну пару кліпс, EUR/пара",
    )

    # 5) Доплата за верхню планку ПВХ зі скотчем (монтаж без свердління), за м.п.
    top_pvc_bar_tape_qty = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Довжина верхньої планки ПВХ зі скотчем, м.п.",
    )
    top_pvc_bar_tape_price_eur_mp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за верхню планку ПВХ зі скотчем, EUR/м.п.",
    )

    # 6) Доплата за широку нижню планку 10/28, за м.п.
    bottom_wide_bar_qty = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Довжина широкої нижньої планки 10/28, м.п.",
    )
    bottom_wide_bar_price_eur_mp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за широку нижню планку 10/28, EUR/м.п.",
    )

    # 7) Фіксація лески металева (шт)
    metal_cord_fix_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість металевих фіксацій лески, шт",
    )
    metal_cord_fix_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна за одну металеву фіксацію лески, EUR/шт",
    )

    # 8) Скотч на верхню планку для встановлення без свердління, за м.п.
    top_bar_scotch_qty = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Довжина скотчу на верхню планку (без свердління), м.п.",
    )
    top_bar_scotch_price_eur_mp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна скотчу на верхню планку, EUR/м.п.",
    )

    # 9) Доплата за електродвигун без пульта (під вимикач), шт
    motor_no_remote_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість електродвигунів без пульта (під вимикач), шт",
    )
    motor_no_remote_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за один електродвигун без пульта, EUR/шт",
    )

    # 10) Доплата за електродвигун з одноканальним пультом ДУ, шт
    motor_with_remote_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість електродвигунів з одноканальним пультом ДУ, шт",
    )
    motor_with_remote_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за електродвигун з одноканальним пультом, EUR/шт",
    )

    # 12) Доплата за 5-ти канальний пульт ДУ, шт
    remote_5ch_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість 5-ти канальних пультів ДУ, шт",
    )
    remote_5ch_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за 5-ти канальний пульт ДУ, EUR/шт",
    )

    # 13) Доплата за 15-ти канальний пульт ДУ, шт
    remote_15ch_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість 15-ти канальних пультів ДУ, шт",
    )
    remote_15ch_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за 15-ти канальний пульт ДУ, EUR/шт",
    )

    # 14) Доплата за проміжковий кронштейн, шт
    middle_bracket_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість проміжкових кронштейнів, шт",
    )
    middle_bracket_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ціна доплати за один проміжковий кронштейн, EUR/шт",
    )
    
    # 15) Доплата за металеві кронштейни, шт								
    metal_kronsht_qty = models.PositiveIntegerField(
        default=0,
        help_text="Кількість металеві кронштейни, шт",
    )
    metal_kronsht_price_eur = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Доплата за металеві кронштейни, EUR/шт",
    )
    
    

    # ---------------------------------------------------------------------
    
    
        # --- Адаптери двигуна Mosel ---
    adapter_mosel_internal_qty = models.PositiveIntegerField(default=0)
    adapter_mosel_internal_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=3.461)

    adapter_mosel_external_qty = models.PositiveIntegerField(default=0)
    adapter_mosel_external_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.797)

    # --- Адаптер короба високий Uni-Besta (м.п.) ---
    adapter_box_high_white_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_high_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.199)

    adapter_box_high_brown_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_high_brown_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.249)

    adapter_box_high_graphite_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_high_graphite_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.837)

    adapter_box_high_oak_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_high_oak_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=4.190)

    # --- Адаптер короба низький для плоскої (м.п.) ---
    adapter_box_low_white_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_low_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.161)

    adapter_box_low_brown_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_low_brown_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.161)

    adapter_box_low_graphite_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adapter_box_low_graphite_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=4.448)

    # --- Вали ---
    shaft_19_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    shaft_19_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=1.048)

    shaft_25_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    shaft_25_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=1.380)

    shaft_32_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    shaft_32_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.749)

    shaft_47_white_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    shaft_47_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=7.437)

    # --- Інші комплектуючі ---
    chain_weight_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    chain_weight_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.084)

    top_profile_dn_al_white_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_profile_dn_al_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=1.397)

    top_profile_dn_al_brown_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_profile_dn_al_brown_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.455)

    top_profile_dn_al_graphite_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_profile_dn_al_graphite_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=2.455)

    top_profile_dn_std_pvc_white_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_profile_dn_std_pvc_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=1.535)

    top_profile_dn_std_pvc_brown_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_profile_dn_std_pvc_brown_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=1.879)

    insert_plus8_white_qty = models.PositiveIntegerField(default=0)
    insert_plus8_white_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.154)

    insert_plus8_brown_qty = models.PositiveIntegerField(default=0)
    insert_plus8_brown_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.154)

    insert_plus8_graphite_qty = models.PositiveIntegerField(default=0)
    insert_plus8_graphite_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.182)

    insert_plus8_oak_qty = models.PositiveIntegerField(default=0)
    insert_plus8_oak_price_eur = models.DecimalField(max_digits=12, decimal_places=3, default=0.182)

 # ---------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    
    eur_rate_at_creation = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Курс EUR на момент створення позиції"
    )

    class Meta:
        ordering = ["id"]

    note = models.TextField(blank=True, verbose_name="Примітка по позиції")

    def __str__(self):
        return f"OrderItem #{self.pk} ({self.system_sheet}/{self.table_section})"

    @property
    def total_eur(self):
        """Total price including quantity of main item (accessories can be включені у subtotal_eur логікою калькулятора)."""
        return float(self.subtotal_eur or 0) * self.quantity
 

class OrderComponentItem(models.Model):
    """
    EN: Single accessory/component line for a given order.
    UA: Окрема позиція комплектуючої для конкретного замовлення.
    """

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="component_items",
        verbose_name="Order",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Найменування",
        help_text="Назва комплектуючої (з аркуша 'Комплектація')",
    )

    unit = models.CharField(
        max_length=32,
        verbose_name="Од. вим.",
        help_text="Одиниця виміру (шт, м.п., компл. тощо)",
    )

    color = models.CharField(
        max_length=64,
        verbose_name="Колір",
        blank=True,
        help_text="Колір комплектуючої (Білий, Графіт, Відсутній тощо)",
    )

    # 🔹 Кількість
    quantity = models.DecimalField(
        max_digits=9,
        decimal_places=3,
        default=1,
        validators=[MinValueValidator(0)],
        verbose_name="Кількість",
        help_text="Кількість у вказаних одиницях виміру (шт, м.п. тощо)",
    )

    # Вартість, Євро за 1 од.
    price_eur = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="Вартість, Євро",
        help_text="Ціна за одиницю в євро (як у прайсі)",
    )

    class Meta:
        verbose_name = "Комплектуюча в замовленні"
        verbose_name_plural = "Комплектуючі в замовленні"

    def __str__(self) -> str:
        return f"{self.name} ({self.color}) – {self.price_eur} € x {self.quantity}"


class OrderStatusLog(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_id}: {self.status} @ {self.created_at}"


class Transaction(models.Model):
    DEBIT = "debit"
    CREDIT = "credit"
    TYPE_CHOICES = [
        (DEBIT, "Пришло від клієнта"),
        (CREDIT, "Уход клієнту"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    # Сума зберігається в EUR (з точністю до 0.00001), вводимо в UAH, перераховуємо по курсу на момент транзакції.
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=5,
        validators=[MinValueValidator(0)],
        help_text="Сума в EUR з підвищеною точністю для точного повернення UAH",
    )
    eur_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Курс EUR/UAH на момент транзакції",
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.type == self.DEBIT else "-"
        return f"{sign}{self.amount} ({self.get_type_display()})"

    @property
    def signed_amount(self):
        return self.amount if self.type == self.DEBIT else -self.amount

    @property
    def amount_uah(self):
        """Сума в гривнях за зафіксованим курсом (попередньо конвертована з EUR)."""
        rate = Decimal(self.eur_rate or 0)
        if not rate:
            # Лише як fallback, якщо курс не заповнено.
            from .services_currency import get_current_eur_rate

            rate = get_current_eur_rate()
        return (Decimal(self.amount or 0) * rate).quantize(Decimal("0.01"))


class CurrencyRate(models.Model):
    """
    EN: Store current currency rates for the project.
    UA: Зберігає актуальні курси валют для проєкту.
    """

    CURRENCY_CHOICES = [
        ("EUR", "Euro"),
        # за потреби можна додати інші валюти
    ]

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        unique=True,
        verbose_name="Валюта",
    )
    rate_uah = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        verbose_name="Курс до UAH",
        help_text="Скільки UAH за 1 одиницю валюти",
    )
    source = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Джерело",
        help_text="Наприклад, NBU, manual",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Оновлено",
    )

    class Meta:
        verbose_name = "Курс валюти"
        verbose_name_plural = "Курси валют"

    def __str__(self):
        return f"{self.currency}: {self.rate_uah} UAH"


class CurrencyRateHistory(models.Model):
    """
    EN: History of currency rate changes.
    UA: Історія змін курсу валют.
    """

    MODE_CHOICES = [
        ("online", "Онлайн"),
        ("manual", "Вручну"),
    ]

    currency = models.CharField(max_length=3, choices=CurrencyRate.CURRENCY_CHOICES)
    rate_uah = models.DecimalField(max_digits=12, decimal_places=4)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="online")
    source = models.CharField(max_length=64, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="currency_rate_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Історія курсу"
        verbose_name_plural = "Історії курсу"

    def __str__(self):
        user_str = f" by {self.user}" if self.user else ""
        return f"{self.currency} {self.rate_uah} ({self.mode}){user_str}"


class OrderDeletionHistory(models.Model):
    """
    EN: Track who deleted orders and when.
    UA: Логи видалення замовлень (хто і коли).
    """

    order_id = models.PositiveIntegerField()
    order_title = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Видалене замовлення"
        verbose_name_plural = "Видалені замовлення"

    def __str__(self):
        return f"Order #{self.order_id} deleted"


class NotificationEmail(models.Model):
    """
    EN: Emails that receive notifications when an order goes to work.
    UA: Email-адреси для сповіщень про відправку замовлення в роботу.
    """

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]
        verbose_name = "Email для сповіщень"
        verbose_name_plural = "Emails для сповіщень"

    def __str__(self):
        return self.email


class PaymentMessage(models.Model):
    """
    EN: Payment reminder / info messages configured by manager.
    UA: Тексти повідомлень для оплати, які задає менеджер.
    """

    text = models.TextField(verbose_name="Текст повідомлення")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Повідомлення для оплати"
        verbose_name_plural = "Повідомлення для оплати"

    def __str__(self):
        return self.text[:50]
