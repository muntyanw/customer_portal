from django.db import models
from django.conf import settings

class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class CustomerProfile(models.Model):
    DELIVERY_PICKUP_PROD = "pickup_prod"
    DELIVERY_PICKUP_OFFICE = "pickup_office"
    DELIVERY_NP = "nova_poshta"
    DELIVERY_ADDRESS = "address_kyiv"

    DELIVERY_CHOICES = [
        (DELIVERY_PICKUP_PROD, "Самовивезення з виробництва"),
        (DELIVERY_PICKUP_OFFICE, "Самовивезення з офісу"),
        (DELIVERY_NP, "Нова Пошта"),
        (DELIVERY_ADDRESS, "Фізична адреса (тільки м. Київ)"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ПІБ")
    contact_email = models.EmailField(blank=True, verbose_name="Email (контактний)")
    trade_address = models.CharField(max_length=255, blank=True, verbose_name="Адреса торгової точки")
    delivery_method = models.CharField(max_length=32, blank=True, choices=DELIVERY_CHOICES, default="")
    delivery_branch = models.CharField(max_length=255, blank=True, verbose_name="Вантажне відділення (від 200кг)")
    note = models.TextField(blank=True, verbose_name="Примітка")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    credit_allowed = models.BooleanField(default=False)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    def __str__(self):
        return f"{self.user.email}"


class CustomerContact(models.Model):
    profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="contacts")
    phone = models.CharField(max_length=32)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.contact_name} ({self.phone})"
