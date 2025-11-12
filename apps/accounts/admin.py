from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "is_customer", "is_manager", "is_staff", "is_superuser")
    search_fields = ("email",)
