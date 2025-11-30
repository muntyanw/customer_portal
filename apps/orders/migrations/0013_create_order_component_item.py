from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0012_remove_magnets_fixation"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderComponentItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),

                # Найменування
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        verbose_name="Найменування",
                        help_text="Назва комплектуючої (з аркуша 'Комплектація')",
                    ),
                ),

                # Од. вим.
                (
                    "unit",
                    models.CharField(
                        max_length=32,
                        verbose_name="Од. вим.",
                        help_text="Одиниця виміру (шт, м.п. тощо)",
                    ),
                ),

                # Колір
                (
                    "color",
                    models.CharField(
                        max_length=64,
                        verbose_name="Колір",
                        blank=True,
                        help_text="Колір комплектуючої (Білий, Графіт, Відсутній тощо)",
                    ),
                ),

                # Кількість
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=9,
                        decimal_places=3,
                        default=1,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Кількість",
                        help_text="Кількість у вказаних одиницях виміру (шт, м.п. тощо)",
                    ),
                ),

                # Цена за единицу
                (
                    "price_eur",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=3,
                        verbose_name="Вартість, Євро",
                        help_text="Ціна за одиницю в євро (як у прайсі)",
                    ),
                ),

                # FK к Order
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="component_items",
                        to="orders.order",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Комплектуюча в замовленні",
                "verbose_name_plural": "Комплектуючі в замовленні",
            },
        ),
    ]
