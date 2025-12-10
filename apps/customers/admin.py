from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Organization, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "organization",
        "phone",
        "contact_email",
        "credit_allowed",
        "create_transaction",
    )
    list_filter = ("credit_allowed", "organization")
    search_fields = ("user__email", "user__username", "full_name", "phone", "contact_email")

    def create_transaction(self, obj):
        url = f"{reverse('orders:transaction_create')}?customer={obj.user_id}"
        return format_html('<a class="button" href="{}">Створити транзакцію</a>', url)

    create_transaction.short_description = "Дії"
    create_transaction.allow_tags = True


admin.site.register(Organization)
