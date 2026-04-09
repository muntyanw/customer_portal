from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0042_ordermosquitoitem_sliding_side_and_warning_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordermosquitoitem",
            name="options_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="ordermosquitoitem",
            name="options_total_usd",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
