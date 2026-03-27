from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0007_customerprofile_discount_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerprofile",
            name="website",
            field=models.URLField(blank=True, verbose_name="Сайт"),
        ),
    ]
