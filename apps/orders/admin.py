from django.contrib import admin
from .models import Order
from apps.accounts.roles import is_manager

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "customer", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "description")

    def has_module_permission(self, request):
        # Доступ до модуля: staff або manager
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or is_manager(request.user) or request.user.is_superuser))

    def has_view_permission(self, request, obj=None):
        # Перегляд: staff/manager — все, customer — нехай через UI, не через admin
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        # Редагування: staff/manager — дозволити
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)
