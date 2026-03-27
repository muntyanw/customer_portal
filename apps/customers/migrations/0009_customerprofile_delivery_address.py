from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0008_customerprofile_website"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerprofile",
            name="delivery_address",
            field=models.CharField(blank=True, max_length=255, verbose_name="Адреса доставки"),
        ),
    ]
