from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0023_transaction_soft_delete"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransactionDeletionHistory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_id", models.IntegerField()),
                ("amount", models.DecimalField(decimal_places=5, max_digits=12)),
                ("customer_email", models.EmailField(max_length=254, blank=True)),
                ("deleted_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="transaction_deletions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
