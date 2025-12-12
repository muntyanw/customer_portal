from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0024_notificationemail"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Текст повідомлення")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Повідомлення для оплати",
                "verbose_name_plural": "Повідомлення для оплати",
            },
        ),
    ]

