def log_audit_event(
    *,
    user=None,
    organization=None,
    action,
    request=None,
    metadata=None,
):
    """
    Central audit logger (safe to call from anywhere)
    """
    from inbox.models import AuditLog

    ip_address = None
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ip_address = xff.split(",")[0]
        else:
            ip_address = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=user,
        organization=organization,
        action=action,
        ip_address=ip_address,
        metadata=metadata or {},
    )
