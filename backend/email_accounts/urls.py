from django.urls import path
from .views import EmailAccountListAPIView, SendEmailAPIView

from .views_signature import (
    MailboxSignatureAPIView,
)

urlpatterns = [
    path(
        'send/',
        SendEmailAPIView.as_view(),
        name='send-email',
    ),

    path(
        "email-accounts/",
        EmailAccountListAPIView.as_view(),
    ),

    path(
        "mailbox-signature/<int:account_id>/",
        MailboxSignatureAPIView.as_view(),
        name="mailbox-signature",
    ),
]
