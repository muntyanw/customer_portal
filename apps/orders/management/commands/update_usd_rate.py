from django.core.management.base import BaseCommand

from apps.orders.services_currency import update_usd_rate_from_nbu


class Command(BaseCommand):
    help = "Fetch USD→UAH rate and store in DB"

    def handle(self, *args, **options):
        obj = update_usd_rate_from_nbu()
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated USD rate: {obj.rate_uah} UAH (source={obj.source})"
            )
        )
