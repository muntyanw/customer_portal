from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0026_order_workbook_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="note",
            field=models.TextField(blank=True, verbose_name="Примітка по позиції"),
        ),
    ]

