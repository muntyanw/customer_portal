from rest_framework import viewsets, permissions
from apps.orders.models import Order
from .serializers import OrderSerializer
from apps.accounts.roles import is_manager

class MyOrdersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/my/orders/ — Customer: тільки свої; Manager: всі.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_manager(user):
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(customer=user).order_by("-created_at")
