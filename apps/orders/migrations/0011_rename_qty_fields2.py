from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_rename_qty_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderitem',
            old_name='top_bar_scotch_m',
            new_name='top_bar_scotch_qty',
        )
    ]
