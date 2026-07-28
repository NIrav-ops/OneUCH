from django.core.management.base import BaseCommand
from inbox.jobs.orphan_cleanup import run


class Command(BaseCommand):
    help = "Cleanup orphaned attachments"

    def handle(self, *args, **options):
        count = run()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} orphaned attachments"
            )
        )
