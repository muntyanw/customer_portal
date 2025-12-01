from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0014_alter_ordercomponentitem_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="eur_rate_at_creation",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=4,
                default=Decimal("0"),
                help_text="Курс EUR/UAH на момент створення замовлення",
            ),
        ),
        migrations.CreateModel(
            name="CurrencyRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "currency",
                    models.CharField(
                        max_length=3,
                        choices=[("EUR", "Euro")],
                        unique=True,
                        verbose_name="Валюта",
                    ),
                ),
                (
                    "rate_uah",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=4,
                        verbose_name="Курс до UAH",
                        help_text="Скільки UAH за 1 одиницю валюти",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        verbose_name="Джерело",
                        help_text="Наприклад, NBU, manual",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Оновлено",
                    ),
                ),
            ],
            options={
                "verbose_name": "Курс валюти",
                "verbose_name_plural": "Курси валют",
            },
        ),
    ]
