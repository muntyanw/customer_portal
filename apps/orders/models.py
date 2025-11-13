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

    # выпадающие
    system_sheet = models.CharField(max_length=128)      # "Фальш-ролети" (название вкладки/системы)
    table_section = models.CharField(max_length=256)     # подзаголовок секции (объединённая ячейка)
    fabric_name  = models.CharField(max_length=128)      # "Тканина"

    # ввод чисел
    height_gabarit_mm = models.PositiveIntegerField()    # ввод руками
    width_fabric_mm   = models.PositiveIntegerField()    # ввод руками

    # инфо
    roll_height_info = models.CharField(max_length=64, blank=True)  # "Висота рулону, мм"

    # флаги/допы
    gabarit_width_flag = models.BooleanField(default=False)   # ширина = по ткани + 4мм
    magnets_fixation   = models.BooleanField(default=False)   # фіксація магніти

    # цены (EUR)
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
