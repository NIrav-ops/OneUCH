from django.utils import timezone

from inbox.models import InboxMessage
from conversations.services import get_or_create_conversation


def save_inbox_message(
    *,
    user,
    platform,
    direction,
    message_id,
    in_reply_to,
    sender,
    recipients,
    subject,
    body,
    received_at=None,
):
    """
    Saves an inbox message and automatically links it to a conversation.
    This is the ONLY place InboxMessage should be created.
    """

    if received_at is None:
        received_at = timezone.now()

    # 1️⃣ Get or create conversation
    conversation = get_or_create_conversation(
        user=user,
        subject=subject,
        participants=recipients.split(","),
        message_id=message_id,
        in_reply_to=in_reply_to,
    )

    # 2️⃣ Save inbox message
    message = InboxMessage.objects.create(
        user=user,
        conversation=conversation,
        platform=platform,
        direction=direction,
        message_id=message_id,
        in_reply_to=in_reply_to,
        sender=sender,
        recipients=recipients,
        subject=subject,
        body=body,
        received_at=received_at,
    )

    return message
