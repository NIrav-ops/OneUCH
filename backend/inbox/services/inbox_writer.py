from inbox.models import InboxMessage


def save_inbox_message(
    subject,
    body,
    sender,
    receiver,
    provider="smtp",
    raw_data=None
):
    """
    Saves an email/message into InboxMessage table
    """

    message = InboxMessage.objects.create(
        subject=subject,
        body=body,
        sender=sender,
        receiver=receiver,
        provider=provider,
        raw_data=raw_data or {},
    )

    return message
