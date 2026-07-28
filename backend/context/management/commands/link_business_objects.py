from django.core.management.base import BaseCommand

from inbox.models import InboxMessage

from context.models import BusinessObjectLink

from context.services import (
    find_business_object,
    link_object,
)


class Command(BaseCommand):

    help = "Automatically links historical emails to Business Objects."

    def handle(self, *args, **options):

        scanned = 0
        linked = 0
        skipped = 0

        messages = InboxMessage.objects.select_related(
            "organization"
        )

        for msg in messages:

            scanned += 1

            business_object = find_business_object(

                msg.organization,

                msg.subject or "",

                msg.body or "",

            )

            if not business_object:

                continue

            exists = BusinessObjectLink.objects.filter(

                business_object=business_object,

                content_type="InboxMessage",

                object_id=msg.id,

            ).exists()

            if exists:

                skipped += 1

                continue

            link_object(

                business_object,

                msg,

                relationship="email",

            )

            linked += 1

            self.stdout.write(

                self.style.SUCCESS(

                    f"Linked: {business_object.name} -> {msg.subject}"

                )

            )

        self.stdout.write("")

        self.stdout.write("=" * 60)

        self.stdout.write(f"Scanned : {scanned}")

        self.stdout.write(f"Linked  : {linked}")

        self.stdout.write(f"Skipped : {skipped}")

        self.stdout.write("=" * 60)