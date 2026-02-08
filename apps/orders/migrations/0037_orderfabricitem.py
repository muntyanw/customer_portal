from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0036_merge_0024_transactiondeletionhistory_0035_order_discount_percent"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderFabricItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fabric_name", models.CharField(max_length=255)),
                ("roll_width_mm", models.PositiveIntegerField(default=0)),
                ("width_mm", models.PositiveIntegerField(default=0)),
                ("included_height_mm", models.PositiveIntegerField(default=0)),
                ("height_mm", models.PositiveIntegerField(default=0)),
                ("price_eur_mp", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("cut_enabled", models.BooleanField(default=False)),
                ("cut_price_eur", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("total_eur", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fabric_items", to="orders.order")),
            ],
            options={
                "verbose_name": "Тканина в замовленні",
                "verbose_name_plural": "Тканини в замовленні",
            },
        ),
    ]
