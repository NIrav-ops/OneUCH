from django.core.management.base import BaseCommand

from inbox.models import InboxMessage

from timeline.models import TimelineEvent


class Command(BaseCommand):

    help = "Backfill timeline events from existing messages"

    def handle(self, *args, **kwargs):

        created = 0

        messages = InboxMessage.objects.select_related(
            "conversation"
        )

        for msg in messages:

            if not msg.conversation:
                continue

            exists = TimelineEvent.objects.filter(

                conversation=msg.conversation,

                event_type="message_received",

                details__external_message_id=str(
                    msg.id
                )

            ).exists()

            if exists:
                continue

            TimelineEvent.objects.create(

                conversation=msg.conversation,

                event_type="message_received",

                title="Historical Email Imported",

                details={

                    "external_message_id": str(
                        msg.id
                    ),

                    "platform": msg.platform,

                    "subject": msg.subject,

                    "sender": msg.sender,

                }

            )

            created += 1

        self.stdout.write(

            self.style.SUCCESS(

                f"Created {created} timeline events"

            )

        )