from datetime import date
from django.utils.timezone import now

from inbox.models import UsageEvent, OrganizationSubscription


class UsageLimitExceeded(Exception):
    pass


def check_usage_limit(organization, event_type):
    """
    Enforce usage limits in real-time using UsageEvent
    """
    try:
        subscription = organization.subscription
    except OrganizationSubscription.DoesNotExist:
        raise UsageLimitExceeded("No active subscription")

    plan = subscription.plan

    # Enterprise = unlimited
    if plan.plan_type == "enterprise":
        return True

    today = date.today()
    period_start = today.replace(day=1)

    # 🔥 REAL-TIME USAGE COUNT (THIS WAS MISSING)
    used = UsageEvent.objects.filter(
        organization=organization,
        event_type=event_type,
        created_at__date__gte=period_start,
    ).count()

    limits = {
        "ATTACHMENT_DOWNLOAD": plan.max_attachment_downloads,
        "ATTACHMENT_PREVIEW": plan.max_attachment_previews,
        "MESSAGE_VIEW": plan.max_message_views,
    }

    limit = limits.get(event_type)

    # No limit defined → allow
    if limit is None:
        return True

    if used >= limit:
        raise UsageLimitExceeded(
            f"{event_type} limit exceeded for plan {plan.name}"
        )

    return True
