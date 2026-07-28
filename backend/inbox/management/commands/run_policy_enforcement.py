from django.core.management.base import BaseCommand
from inbox.jobs.policy_enforcement import run


class Command(BaseCommand):
    help = "Enforce attachment policies and flag violations"

    def handle(self, *args, **options):
        count = run()

        self.stdout.write(
            self.style.SUCCESS(
                f"Flagged {count} attachments violating policy"
            )
        )
