from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import MyOrdersViewSet
from .pricing_views import (
    systems_list,
    system_fabrics,
    system_preview,
    fabric_colors,
)

router = DefaultRouter()
router.register(r"my/orders", MyOrdersViewSet, basename="my-orders")

urlpatterns = [
    path("", include(router.urls)),

    # New pricing API (all sheets, no legacy)
    path("pricing/systems-list", systems_list, name="pricing-systems-list"),
    path("pricing/system-fabrics", system_fabrics, name="pricing-system-fabrics"),
    path("pricing/system-preview", system_preview, name="pricing-system-preview"),
    path("pricing/fabric-colors", fabric_colors, name="fabric_colors"),

]

