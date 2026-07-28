from django.db.models import Count
from datetime import date

from inbox.models import UsageEvent, UsageSummary


def run(period_start, period_end):
    """
    Aggregate raw usage events into usage summaries
    """
    events = (
        UsageEvent.objects
        .filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
        )
        .values("organization_id", "event_type")
        .annotate(total=Count("id"))
    )

    summary_map = {}

    for row in events:
        org_id = row["organization_id"]
        event_type = row["event_type"]
        total = row["total"]

        summary_map.setdefault(org_id, {
            "ATTACHMENT_DOWNLOAD": 0,
            "ATTACHMENT_PREVIEW": 0,
            "MESSAGE_VIEW": 0,
        })

        summary_map[org_id][event_type] = total

    created = 0
    for org_id, data in summary_map.items():
        UsageSummary.objects.update_or_create(
            organization_id=org_id,
            period_start=period_start,
            period_end=period_end,
            defaults={
                "attachment_downloads": data["ATTACHMENT_DOWNLOAD"],
                "attachment_previews": data["ATTACHMENT_PREVIEW"],
                "message_views": data["MESSAGE_VIEW"],
            },
        )
        created += 1

    return created
