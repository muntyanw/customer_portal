from decimal import Decimal

from django.db import migrations, models


def set_initial_rate(apps, schema_editor):
    Transaction = apps.get_model("orders", "Transaction")
    CurrencyRate = apps.get_model("orders", "CurrencyRate")

    last_rate = (
        CurrencyRate.objects.filter(currency="EUR").order_by("-updated_at").first()
    )
    rate = last_rate.rate_uah if last_rate else Decimal("0")
    Transaction.objects.filter(eur_rate=Decimal("0")).update(eur_rate=rate)


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0020_order_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="eur_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0"),
                help_text="Курс EUR/UAH на момент транзакції",
                max_digits=12,
            ),
        ),
        migrations.RunPython(set_initial_rate, migrations.RunPython.noop),
    ]
