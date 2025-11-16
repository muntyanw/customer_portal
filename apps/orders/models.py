#apps/orders/models.py
from django.db import models
from django.conf import settings

class Order(models.Model):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"
    STATUS_CHOICES = [
        (NEW, "New"),
        (IN_PROGRESS, "In progress"),
        (DONE, "Done"),
        (CANCELED, "Canceled"),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW)
    attachment = models.FileField(upload_to="attachments/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.pk} {self.title}"
    
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    organization = models.ForeignKey("customers.Organization", on_delete=models.PROTECT, null=True, blank=True)

    # Selects
    system_sheet = models.CharField(max_length=128)      # назва вкладки (система)
    table_section = models.CharField(max_length=256)     # заголовок секції (колір системи)
    fabric_name  = models.CharField(max_length=128)      # назва тканини
    
    fabric_color_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Код кольору тканини",
    )

    # Numeric input
    height_gabarit_mm = models.PositiveIntegerField()    # габаритна висота, мм
    width_fabric_mm   = models.PositiveIntegerField()    # введена ширина, мм (зараз = по тканині; логіку можна змінити пізніше)

    # Info
    roll_height_info = models.CharField(max_length=64, blank=True)  # "Висота рулону, мм"

    # Flags / options
    gabarit_width_flag = models.BooleanField(default=False)   # галочка "Габаритна ширина (+4мм)" / "ширина габаритна"
    magnets_fixation   = models.BooleanField(default=False)   # фіксація магнітами (з прайсу)
    bottom_fixation    = models.BooleanField(default=False)   # нижня фіксація (логічний прапорець, без ціни поки)
    pvc_plank          = models.BooleanField(default=False)   # планка ПВХ зі скотчем (логічний прапорець, без ціни поки)

    # Control side
    control_side = models.CharField(
        max_length=32,
        blank=True,
        help_text="Сторона керування (лівий/правий ланцюжок тощо)",
    )

    # Prices (EUR)
    base_price_eur       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    surcharge_height_eur = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    magnets_price_eur    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal_eur         = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    quantity = models.PositiveIntegerField(default=1, help_text="Кількість однакових виробів у цій позиції")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"OrderItem #{self.pk} ({self.system_sheet}/{self.table_section})"

    @property
    def total_eur(self):
        """Сумарна ціна з урахуванням кількості"""
        return float(self.subtotal_eur or 0) * self.quantity
