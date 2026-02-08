from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import MyOrdersViewSet
from .pricing_views import (
    systems_list,
    system_fabrics,
    system_preview,
    fabric_colors,
    system_config,
    components_list,
    fabrics_list,
    fabric_preview,
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
    path("pricing/system-config", system_config, name="pricing-system-config"),
    path(
        "pricing/components-list",
        components_list,
        name="pricing-components-list",
    ),
    path("pricing/fabrics-list", fabrics_list, name="pricing-fabrics-list"),
    path("pricing/fabric-preview", fabric_preview, name="pricing-fabric-preview"),


]
