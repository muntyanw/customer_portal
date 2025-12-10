from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0017_orderitem_gbdiffwidthmm_orderitem_gb_width_mm"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="eur_rate",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=4,
                default=Decimal("0"),
                help_text="Курс EUR/UAH, що застосовано для цього замовлення",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="markup_percent",
            field=models.DecimalField(
                max_digits=6,
                decimal_places=2,
                default=Decimal("0"),
                help_text="Процент націнки, що застосовано до замовлення",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="total_eur",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                default=Decimal("0"),
                help_text="Підсумкова сума замовлення в EUR (з націнкою)",
            ),
        ),
    ]
