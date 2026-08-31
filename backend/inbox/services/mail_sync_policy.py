from dataclasses import (
    dataclass,
)

from datetime import (
    timedelta,
)

from django.db.models import (
    Max,
)

from django.utils import (
    timezone,
)

from inbox.models import (
    InboxMessage,
)


INITIAL_HISTORY_DAYS = 90

# Re-read a small overlap after the initial backfill. Provider
# IDs remain authoritative for deduplication, so the overlap
# protects against timestamp/order boundaries without creating
# duplicate One UCH messages.
INCREMENTAL_OVERLAP_DAYS = 1

GMAIL_PAGE_SIZE = 100
OUTLOOK_PAGE_SIZE = 100


@dataclass(
    frozen=True,
)
class MailSyncWindow:

    cutoff: object

    initial_history: bool


def resolve_mail_sync_window(
    *,
    email_account,
    now=None,
):
    current_time = (
        now
        or timezone.now()
    )


    if (
        email_account
        .history_sync_completed_at
        is None
    ):

        return MailSyncWindow(
            cutoff=(
                current_time
                - timedelta(
                    days=(
                        INITIAL_HISTORY_DAYS
                    )
                )
            ),
            initial_history=True,
        )


    latest_message_at = (
        InboxMessage.objects
        .filter(
            email_account=(
                email_account
            ),
            is_draft=False,
        )
        .aggregate(
            latest=Max(
                "received_at"
            )
        )
        .get(
            "latest"
        )
    )


    anchor = (
        latest_message_at
        or
        email_account
        .history_sync_completed_at
    )


    return MailSyncWindow(
        cutoff=(
            anchor
            - timedelta(
                days=(
                    INCREMENTAL_OVERLAP_DAYS
                )
            )
        ),
        initial_history=False,
    )


def mark_initial_history_complete(
    *,
    email_account,
    completed_at=None,
):
    if (
        email_account
        .history_sync_completed_at
        is not None
    ):
        return False


    email_account.history_sync_completed_at = (
        completed_at
        or timezone.now()
    )

    email_account.save(
        update_fields=[
            "history_sync_completed_at",
        ]
    )

    return True
