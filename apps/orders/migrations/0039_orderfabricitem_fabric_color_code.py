from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0038_alter_transactiondeletionhistory_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderfabricitem",
            name="fabric_color_code",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
