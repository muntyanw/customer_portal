from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerprofile",
            name="credit_allowed",
            field=models.BooleanField(default=False),
        ),
    ]
