from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("customers/", include("apps.customers.urls")),
    path("orders/", include("apps.orders.urls")),
    path("api/", include("apps.api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
