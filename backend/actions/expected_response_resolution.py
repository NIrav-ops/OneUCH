from email.utils import parseaddr

from django.utils import timezone

from actions.models import ExpectedResponseItem


def resolve_expected_responses_for_message(
    message,
):
    """
    Resolve waiting ExpectedResponseItems using a
    later inbound message from the same conversation.

    Conservative rules:

    - Only inbound messages may resolve.
    - Message must belong to a conversation.
    - Only items in "waiting" status are eligible.
    - Response must be later than the source message.
    - If expected_from is known, sender must match.
    - If expected_from is unknown, any later inbound
      message in the same conversation may resolve.
    """

    if message is None:
        return 0

    if message.direction != "inbound":
        return 0

    if not message.conversation_id:
        return 0

    waiting_items = (
        ExpectedResponseItem.objects
        .filter(
            conversation_id=message.conversation_id,
            status="waiting",
        )
        .select_related(
            "source_message"
        )
        .order_by(
            "created_at"
        )
    )

    resolved_count = 0

    sender = (
        parseaddr(
            message.sender or ""
        )[1]
        .strip()
        .lower()
    )

    for item in waiting_items:
        source = item.source_message

        if source is None:
            continue

        if (
            message.received_at
            <= source.received_at
        ):
            continue

        expected_from = (
            (item.expected_from or "")
            .strip()
            .lower()
        )

        if (
            expected_from
            and sender != expected_from
        ):
            continue

        item.status = "received"
        item.resolved_by_message = message
        item.resolved_at = (
            message.received_at
            or timezone.now()
        )

        item.save(
            update_fields=[
                "status",
                "resolved_by_message",
                "resolved_at",
                "updated_at",
            ]
        )

        resolved_count += 1

    return resolved_count
