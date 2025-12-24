from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion
from decimal import Decimal
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0031_order_extra_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="order",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="order",
            name="deleted_by",
            field=models.ForeignKey(
                related_name="soft_deleted_orders",
                on_delete=django.db.models.deletion.SET_NULL,
                blank=True,
                null=True,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
