from django.contrib import admin
from .models import Organization, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "organization", "phone", "contact_email", "credit_allowed")
    list_filter = ("credit_allowed", "organization")
    search_fields = ("user__email", "user__username", "full_name", "phone", "contact_email")


admin.site.register(Organization)
