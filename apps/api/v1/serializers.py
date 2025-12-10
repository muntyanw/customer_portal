from rest_framework import serializers
from apps.orders.models import Order

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "title",
            "description",
            "status",
            "total_eur",
            "eur_rate",
            "markup_percent",
            "created_at",
        ]
