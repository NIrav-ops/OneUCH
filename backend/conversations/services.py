from inbox.models import Conversation
from conversations.utils import normalize_subject


def get_or_create_conversation(
    *,
    user,
    subject,
    participants,
    message_id=None,
    in_reply_to=None
):
    # 1️⃣ Try reply-chain match
    if in_reply_to:
        existing = Conversation.objects.filter(
            user=user,
            subject__iexact=subject
        ).first()
        if existing:
            return existing

    # 2️⃣ Normalize subject match
    normalized = normalize_subject(subject)

    conversation = Conversation.objects.filter(
        user=user,
        subject__iexact=normalized
    ).first()

    if conversation:
        return conversation

    # 3️⃣ Create new conversation
    return Conversation.objects.create(
        user=user,
        subject=normalized,
        participants=",".join(participants),
    )

