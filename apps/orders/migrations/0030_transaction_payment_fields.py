from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0029_orderdeletionhistory"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="account_number",
            field=models.CharField(blank=True, max_length=128, verbose_name="Номер рахунку"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="payment_type",
            field=models.CharField(
                choices=[("cash", "Готівка"), ("account", "На рахунок")],
                default="account",
                max_length=16,
                verbose_name="Вид оплати",
            ),
        ),
    ]
