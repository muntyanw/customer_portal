from django.db import migrations, models
import django.conf


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0028_currencyratehistory"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderDeletionHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("order_id", models.PositiveIntegerField()),
                ("order_title", models.CharField(blank=True, max_length=255)),
                ("customer_email", models.EmailField(blank=True, max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deleted_orders",
                        to=django.conf.settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Видалене замовлення",
                "verbose_name_plural": "Видалені замовлення",
            },
        ),
    ]
