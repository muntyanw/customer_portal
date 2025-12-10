from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0018_order_totals_and_markup"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("quote", "Прорахунок"),
                    ("in_work", "В роботі"),
                    ("ready_for_pickup", "Готовий до вивозу"),
                    ("shipped", "Відвантажено"),
                ],
                default="quote",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="OrderStatusLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("quote", "Прорахунок"), ("in_work", "В роботі"), ("ready_for_pickup", "Готовий до вивозу"), ("shipped", "Відвантажено")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("note", models.TextField(blank=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_logs", to="orders.order")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_status_changes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(choices=[("debit", "Дебет"), ("credit", "Кредит")], max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(0)])),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_transactions", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="transactions", to="orders.order")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
