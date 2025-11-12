from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MyOrdersViewSet

router = DefaultRouter()
router.register(r"my/orders", MyOrdersViewSet, basename="my-orders")

urlpatterns = [
    path("", include(router.urls)),
]
