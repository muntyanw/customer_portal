from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0023_alter_transaction_amount_precision"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["email"],
                "verbose_name": "Email для сповіщень",
                "verbose_name_plural": "Emails для сповіщень",
            },
        ),
    ]

