from django.core.management.base import BaseCommand
from apps.orders.services_currency import update_eur_rate_from_nbu


class Command(BaseCommand):
    help = "Fetch EUR→UAH rate from NBU and store in DB"

    def handle(self, *args, **options):
        obj = update_eur_rate_from_nbu()
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated EUR rate: {obj.rate_uah} UAH (source={obj.source})"
            )
        )
