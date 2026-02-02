from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0006_alter_customercontact_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerprofile",
            name="discount_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]

