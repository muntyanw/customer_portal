# apps/orders/admin.py
from django.contrib import admin, messages
from .models import (
    Order,
    OrderItem,
    OrderComponentItem,
    CurrencyRate,
    OrderStatusLog,
    Transaction,
    NotificationEmail,
    PaymentMessage,
)
from .services_currency import update_eur_rate_from_nbu


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate_uah", "source", "updated_at")
    list_filter = ("currency", "source")
    search_fields = ("currency",)
    readonly_fields = ("updated_at",)

    actions = ["fetch_eur_from_nbu"]

    @admin.action(description="Оновити курс EUR з НБУ")
    def fetch_eur_from_nbu(self, request, queryset):
        obj = update_eur_rate_from_nbu()
        self.message_user(
            request,
            f"Курс EUR оновлено: {obj.rate_uah} грн (джерело: {obj.source})",
            level=messages.SUCCESS,
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "customer",
        "status",
        "total_eur",
        "markup_percent",
        "eur_rate",
        "created_at",
        "eur_rate_at_creation",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "customer__email", "customer__username")


admin.site.register(OrderItem)
admin.site.register(OrderComponentItem)


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "user", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__id", "user__email", "user__username")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "type", "amount", "eur_rate", "order", "created_by", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("customer__email", "customer__username")


@admin.register(NotificationEmail)
class NotificationEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email",)


@admin.register(PaymentMessage)
class PaymentMessageAdmin(admin.ModelAdmin):
    list_display = ("short_text", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("text",)

    def short_text(self, obj):
        return (obj.text or "")[:60]
    short_text.short_description = "Текст"
