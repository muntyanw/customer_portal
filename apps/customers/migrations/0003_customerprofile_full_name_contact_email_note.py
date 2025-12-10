from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0002_customerprofile_credit_allowed"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerprofile",
            name="contact_email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="Email (контактний)"),
        ),
        migrations.AddField(
            model_name="customerprofile",
            name="full_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="ПІБ"),
        ),
        migrations.AddField(
            model_name="customerprofile",
            name="note",
            field=models.TextField(blank=True, verbose_name="Примітка"),
        ),
    ]
