from django.core.files.base import ContentFile
from inbox.models import Attachment
from .services.virus_scan import scan_attachment


def normalize_gmail_message(detail):
    return {
        "message_id": detail.get("id"),
        "subject": detail.get("payload", {}).get("headers", [{}])[0].get("value", ""),
        "sender": "",
        "recipients": "",
        "body": "",
    }


def normalize_outlook_message(msg):
    return {
        "message_id": msg.get("id"),
        "subject": msg.get("subject", ""),
        "sender": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
        "recipients": "",
        "body": msg.get("bodyPreview", ""),
    }


# ✅ THIS IS THE IMPORTANT PART
def save_attachment(*, inbox_message, filename, content_type, content_bytes):
    """
    Save an attachment securely and link it to an inbox message
    """

    attachment = Attachment.objects.create(
        message=inbox_message,
        filename=filename,
        content_type=content_type,
        size=len(content_bytes),
    )

    attachment.file.save(
        filename,
        ContentFile(content_bytes),
        save=True
    )
     # 🦠 Virus scan hook
    scan_attachment(attachment)

    return attachment
