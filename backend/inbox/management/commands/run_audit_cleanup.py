from django.core.management.base import BaseCommand
from inbox.jobs.audit_cleanup import run


class Command(BaseCommand):
    help = "Cleanup old audit logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days to keep audit logs",
        )

    def handle(self, *args, **options):
        days = options["days"]
        deleted = run(days_to_keep=days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} audit log records older than {days} days"
            )
        )
