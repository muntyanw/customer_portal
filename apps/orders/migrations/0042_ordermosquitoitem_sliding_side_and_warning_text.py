from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0041_alter_currencyrate_currency_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordermosquitoitem",
            name="sliding_side",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="ordermosquitoitem",
            name="warning_text",
            field=models.TextField(blank=True, default=""),
        ),
    ]
