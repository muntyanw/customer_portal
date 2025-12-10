from django.db import models
from django.conf import settings

class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ПІБ")
    contact_email = models.EmailField(blank=True, verbose_name="Email (контактний)")
    note = models.TextField(blank=True, verbose_name="Примітка")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    credit_allowed = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user.email}"
