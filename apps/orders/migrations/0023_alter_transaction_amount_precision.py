from django.db import migrations, models
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0022_alter_transaction_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="amount",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=5,
                validators=[MinValueValidator(0)],
                help_text="Сума в EUR з підвищеною точністю для точного повернення UAH",
            ),
        ),
    ]
