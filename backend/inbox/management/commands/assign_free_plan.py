from datetime import date
from django.core.management.base import BaseCommand

from inbox.models import Organization, BillingPlan, OrganizationSubscription


class Command(BaseCommand):
    help = "Assign FREE plan to organizations without subscription"

    def handle(self, *args, **options):
        free_plan = BillingPlan.objects.get(code="FREE")

        count = 0
        for org in Organization.objects.all():
            sub, created = OrganizationSubscription.objects.get_or_create(
                organization=org,
                defaults={
                    "plan": free_plan,
                    "start_date": date.today(),
                },
            )
            if created:
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned FREE plan to {count} organizations"
            )
        )
