from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0019_status_flow_transactions"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="note",
            field=models.TextField(blank=True, verbose_name="Примітка"),
        ),
    ]
