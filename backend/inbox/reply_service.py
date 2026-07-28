from django.utils import timezone
from inbox.models import InboxMessage
from email_accounts.models import EmailAccount
from email_accounts.services.gmail_api import send_gmail_reply
from email_accounts.services.imap_smtp import send_via_smtp
from oauth_tokens.models import OAuthToken
from email_accounts.services.microsoft_api import send_outlook_reply


def send_reply(user, conversation, body):
    """
    Unified reply engine.
    Priority:
    1. Gmail OAuth (if connected)
    2. IMAP/SMTP fallback

    ALWAYS returns InboxMessage
    """

    # 1️⃣ Prefer Gmail OAuth if token exists
    google_token_exists = OAuthToken.objects.filter(
        user=user,
        provider="google",
        is_active=True
    ).exists()

    if google_token_exists:
        send_gmail_reply(
            user=user,
            to_email=conversation.participants,
            subject=conversation.subject,
            body=body,
        )

        # ✅ STORE SENT MESSAGE
        return InboxMessage.objects.create(
            user=user,
            conversation=conversation,
            platform="gmail",
            direction="out",
            message_id=f"gmail-out-{timezone.now().timestamp()}",
            in_reply_to=None,
            sender=user.email,
            recipients=conversation.participants,
            subject=conversation.subject,
            body=body,
            received_at=timezone.now(),
        )
    
    microsoft_token_exists = OAuthToken.objects.filter(
    user=user,
    provider="microsoft",
    is_active=True
).exists()

    if microsoft_token_exists:
        send_outlook_reply(
        user=user,
        to_email=conversation.participants,
        subject=conversation.subject,
        body=body,
    )
    return InboxMessage.objects.create(
        user=user,
        conversation=conversation,
        platform="outlook",
        direction="out",
        message_id=f"ms-out-{timezone.now().timestamp()}",
        sender=user.email,
        recipients=conversation.participants,
        subject=conversation.subject,
        body=body,
        received_at=timezone.now(),
    )


    # 2️⃣ Fallback to IMAP/SMTP
    email_account = EmailAccount.objects.filter(
        user=user,
        is_active=True
    ).first()

    if not email_account:
        raise Exception("No active email account found")

    send_via_smtp(
        email_account=email_account,
        to_email=conversation.participants,
        subject=conversation.subject,
        body=body,
    )

    return InboxMessage.objects.create(
        user=user,
        conversation=conversation,
        platform=email_account.account_type,
        direction="out",
        message_id=f"smtp-out-{timezone.now().timestamp()}",
        in_reply_to=None,
        sender=email_account.email_address,
        recipients=conversation.participants,
        subject=conversation.subject,
        body=body,
        received_at=timezone.now(),
    )
