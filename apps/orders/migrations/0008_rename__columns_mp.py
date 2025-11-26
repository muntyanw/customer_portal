from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_orderitem_metal_kronsht_price_eur_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE orders_orderitem
                    RENAME COLUMN top_pvc_bar_tape_price_eur
                        TO top_pvc_bar_tape_price_eur_mp;

                ALTER TABLE orders_orderitem
                    RENAME COLUMN bottom_wide_bar_price_eur
                        TO bottom_wide_bar_price_eur_mp;
            """,
            reverse_sql="""
                ALTER TABLE orders_orderitem
                    RENAME COLUMN top_pvc_bar_tape_price_eur_mp
                        TO top_pvc_bar_tape_price_eur;

                ALTER TABLE orders_orderitem
                    RENAME COLUMN bottom_wide_bar_price_eur_mp
                        TO bottom_wide_bar_price_eur;
            """
        )
    ]
