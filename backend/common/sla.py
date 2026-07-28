from django.utils import timezone


def calculate_sla(due_date, status):

    if not due_date:
        return "green"

    if status in [
        "completed",
        "approved",
        "ignored",
    ]:
        return "green"

    now = timezone.now()

    remaining = due_date - now

    hours = remaining.total_seconds() / 3600

    if hours < 0:
        return "red"

    if hours <= 24:
        return "yellow"

    return "green"