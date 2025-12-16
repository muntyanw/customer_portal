from django.db import migrations, models
import django.conf


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0027_orderitem_note"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CurrencyRateHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("currency", models.CharField(choices=[("EUR", "Euro")], max_length=3)),
                ("rate_uah", models.DecimalField(decimal_places=4, max_digits=12)),
                (
                    "mode",
                    models.CharField(
                        choices=[("online", "Онлайн"), ("manual", "Вручну")],
                        default="online",
                        max_length=16,
                    ),
                ),
                ("source", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="currency_rate_changes",
                        to=django.conf.settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Історія курсу",
                "verbose_name_plural": "Історії курсу",
                "ordering": ["-created_at"],
            },
        ),
    ]
