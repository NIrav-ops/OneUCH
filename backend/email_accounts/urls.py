from django.urls import path

from .views import (
    EmailAccountListAPIView,
    SendEmailAPIView,
)

from .views_other_work_email import (
    OtherWorkEmailSetupAPIView,
    OtherWorkEmailSyncAPIView,
)

from .views_signature import (
    MailboxSignatureAPIView,
)


urlpatterns = [
    path(
        "send/",
        SendEmailAPIView.as_view(),
        name="send-email",
    ),

    path(
        "email-accounts/",
        EmailAccountListAPIView.as_view(),
    ),

    path(
        "other-work-email/",
        OtherWorkEmailSetupAPIView.as_view(),
        name="other-work-email-setup",
    ),

    path(
        "other-work-email/<int:account_id>/sync/",
        OtherWorkEmailSyncAPIView.as_view(),
        name="other-work-email-sync",
    ),

    path(
        "mailbox-signature/<int:account_id>/",
        MailboxSignatureAPIView.as_view(),
        name="mailbox-signature",
    ),
]
