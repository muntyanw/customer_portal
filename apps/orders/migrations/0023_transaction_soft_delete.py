from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0034_merge_0032_order_soft_delete_0033_merge_20251224_2317"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="transaction",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="deleted_transactions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
