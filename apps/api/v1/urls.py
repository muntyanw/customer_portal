from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MyOrdersViewSet
from .pricing_views import sheets_list, fabrics_first, preview_first, sections_first, fabrics_first_section


router = DefaultRouter()
router.register(r"my/orders", MyOrdersViewSet, basename="my-orders")

urlpatterns = [
    path("", include(router.urls)),
    path("pricing/sheets", sheets_list, name="pricing-sheets"),
    path("pricing/fabrics-first", fabrics_first, name="pricing-fabrics-first"),
    path("pricing/preview-first", preview_first, name="pricing-preview-first"),
    path("pricing/sections-first", sections_first, name="pricing-sections-first"),
    path("pricing/fabrics-first-section", fabrics_first_section, name="pricing-fabrics-first-section"),
    path("pricing/preview-first", preview_first, name="pricing-preview-first"),
]
