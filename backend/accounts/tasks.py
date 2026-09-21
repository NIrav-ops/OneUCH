from celery import (
    shared_task,
)

from accounts.registration_notifications import (
    send_registration_approval_email,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.registration.notification"
)


@shared_task(
    bind=True,
    max_retries=3,
)
def send_registration_approval_email_task(
    self,
    registration_public_id,
):

    try:

        result = (
            send_registration_approval_email(
                registration_public_id
            )
        )

        log_event(
            logger,
            "info",
            "registration.approval_email.sent",
            registration_id=(
                registration_public_id
            ),
        )

        return result

    except Exception as exc:

        log_event(
            logger,
            "warning",
            "registration.approval_email.failed",
            registration_id=(
                registration_public_id
            ),
            error_type=(
                type(exc).__name__
            ),
        )

        if (
            self.request.retries
            >=
            self.max_retries
        ):

            return {
                "status":
                    "failed",

                "registration_id":
                    registration_public_id,
            }

        raise self.retry(
            exc=RuntimeError(
                "Approval email delivery failed."
            ),
            countdown=(
                60
                *
                (
                    2
                    **
                    self.request.retries
                )
            ),
        )
