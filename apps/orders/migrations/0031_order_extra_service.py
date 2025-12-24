from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0030_transaction_payment_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="extra_service_label",
            field=models.CharField(
                default="",
                blank=True,
                max_length=255,
                help_text="Назва додаткової послуги",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="extra_service_amount_uah",
            field=models.DecimalField(
                default=Decimal("0"),
                max_digits=12,
                decimal_places=2,
                help_text="Сума додаткової послуги, грн",
            ),
        ),
    ]
