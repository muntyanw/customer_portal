from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_orderitem_magnets_qty'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderitem',
            old_name='top_pvc_bar_tape_m',
            new_name='top_pvc_bar_tape_qty',
        ),
        migrations.RenameField(
            model_name='orderitem',
            old_name='bottom_wide_bar_m',
            new_name='bottom_wide_bar_qty',
        ),
    ]
