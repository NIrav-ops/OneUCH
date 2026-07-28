from inbox.models import Conversation
from inbox.models import InboxMessage


def get_or_create_conversation(user, subject, participants, in_reply_to=None):
    if in_reply_to:
        msg = InboxMessage.objects.filter(
            message_id=in_reply_to,
            user=user
        ).first()

        if msg:
            return msg.conversation

    return Conversation.objects.create(
        user=user,
        subject=subject,
        participants=",".join(participants)
    )
