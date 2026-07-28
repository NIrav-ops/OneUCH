from django.core.management.base import BaseCommand
from inbox.models import BillingPlan


class Command(BaseCommand):
    help = "Create default SaaS billing plans"

    def handle(self, *args, **options):
        plans = [
            {
                "name": "Free",
                "code": "FREE",
                "plan_type": "free",
                "price_monthly": 0,
                "max_attachment_downloads": 100,
                "max_attachment_previews": 200,
                "max_message_views": 500,
            },
            {
                "name": "Pro",
                "code": "PRO",
                "plan_type": "pro",
                "price_monthly": 999,
                "max_attachment_downloads": 10000,
                "max_attachment_previews": 20000,
                "max_message_views": 50000,
            },
            {
                "name": "Enterprise",
                "code": "ENT",
                "plan_type": "enterprise",
                "price_monthly": 0,
                "max_attachment_downloads": None,
                "max_attachment_previews": None,
                "max_message_views": None,
            },
        ]

        for plan_data in plans:
            BillingPlan.objects.update_or_create(
                code=plan_data["code"],
                defaults=plan_data,
            )

        self.stdout.write(
            self.style.SUCCESS("Default billing plans created / updated")
        )
