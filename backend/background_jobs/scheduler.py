from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

from background_jobs.tasks import (
    refresh_oauth_tokens,
    fetch_all_imap_inboxes
)


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

    # OAuth refresh every 10 minutes
    scheduler.add_job(
        refresh_oauth_tokens,
        trigger='interval',
        minutes=10,
        id='refresh_oauth_tokens',
        replace_existing=True
    )

    # IMAP fetch every 5 minutes
    scheduler.add_job(
        fetch_all_imap_inboxes,
        trigger='interval',
        minutes=5,
        id='fetch_all_imap_inboxes',
        replace_existing=True
    )

    scheduler.start()
