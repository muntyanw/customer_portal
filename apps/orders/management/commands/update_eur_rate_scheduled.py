from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders.models import CurrencyAutoUpdateSettings, CurrencyRateHistory
from apps.orders.services_currency import update_eur_rate_from_nbu


class Command(BaseCommand):
    help = "Update EUR rate if auto-update is enabled and scheduled for current time"

    def handle(self, *args, **options):
        settings_obj = CurrencyAutoUpdateSettings.get_solo()
        if not settings_obj.auto_update:
            self.stdout.write("Auto-update disabled.")
            return

        if not settings_obj.update_times:
            self.stdout.write("No update times configured.")
            return

        now_local = timezone.localtime()
        current_time = now_local.strftime("%H:%M")
        if current_time not in settings_obj.update_times:
            self.stdout.write(f"No update scheduled for {current_time}.")
            return

        obj = update_eur_rate_from_nbu()
        CurrencyRateHistory.objects.create(
            currency=obj.currency,
            rate_uah=obj.rate_uah,
            mode="online",
            source=obj.source,
            user=None,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated EUR rate: {obj.rate_uah} UAH (source={obj.source})"
            )
        )
