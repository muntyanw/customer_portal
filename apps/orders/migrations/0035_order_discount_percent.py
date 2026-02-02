from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0034_merge_0032_order_soft_delete_0033_merge_20251224_2317"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="discount_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=6),
        ),
    ]

