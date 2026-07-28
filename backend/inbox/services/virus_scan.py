from django.utils import timezone


def scan_attachment(attachment):
    """
    Virus scan hook.
    This is a placeholder for future integrations like:
    - ClamAV
    - AWS Malware Protection
    - Paid AV APIs

    For now, we mark everything as clean.
    """

    try:
        # 🔮 FUTURE:
        # run actual AV scan here

        attachment.scan_status = "clean"
        attachment.scanned_at = timezone.now()
        attachment.save(update_fields=["scan_status", "scanned_at"])
    
        return True

    except Exception:
        attachment.scan_status = "failed"
        attachment.scanned_at = timezone.now()
        attachment.save(update_fields=["scan_status", "scanned_at"])
        return False
