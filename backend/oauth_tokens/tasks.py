from celery import shared_task
from django.utils import timezone
from oauth_tokens.models import OAuthToken
from oauth_tokens.services import refresh_google_token


@shared_task
def refresh_expired_tokens():
    tokens = OAuthToken.objects.filter(
        is_active=True,
        expires_at__lte=timezone.now()
    )

    for token in tokens:
        if token.provider == "google":
            refresh_google_token(token)
