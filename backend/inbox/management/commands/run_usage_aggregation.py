from datetime import date
from django.core.management.base import BaseCommand

from inbox.jobs.usage_aggregation import run


class Command(BaseCommand):
    help = "Aggregate usage metrics for billing"

    def handle(self, *args, **options):
        today = date.today()
        period_start = today.replace(day=1)
        period_end = today

        count = run(period_start, period_end)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated usage summaries for {count} organizations"
            )
        )
