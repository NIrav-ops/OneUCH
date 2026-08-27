from celery import shared_task
from django.utils import timezone

from audit_logs.models import AuditLog
from microsoftapis.utils import refresh_microsoft_token
from oauth_tokens.models import OAuthToken
from oauth_tokens.services import refresh_google_token


@shared_task
def refresh_expired_tokens():

    tokens = OAuthToken.objects.filter(
        is_active=True,
        expires_at__lte=timezone.now(),
    )

    for token in tokens:

        try:

            if token.provider == "google":

                refresh_google_token(
                    token
                )

            elif token.provider == "microsoft":

                refresh_microsoft_token(
                    token
                )

        except Exception as exc:

            AuditLog.objects.create(
                user=token.user,
                action="oauth_refresh_failed",
                platform=token.provider,
                description=str(exc),
            )
