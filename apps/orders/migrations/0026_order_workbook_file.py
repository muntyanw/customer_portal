from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0025_paymentmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="workbook_file",
            field=models.FileField(blank=True, null=True, upload_to="order_exports/"),
        ),
    ]

