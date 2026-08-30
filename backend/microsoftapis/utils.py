import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from oauth_tokens.models import OAuthToken
from oauth_tokens.policy import enforce_oauth_execution_policy


def refresh_microsoft_token(oauth_token):

    enforce_oauth_execution_policy(
        token=oauth_token,
        provider="microsoft",
    )

    response = requests.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data={
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "refresh_token": oauth_token.refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        },
    )

    data = response.json()

    if "access_token" not in data:

        oauth_token.is_active = False
        oauth_token.save(update_fields=["is_active"])

        raise Exception(
            f"Microsoft token refresh failed: {data}"
        )

    access_token = data["access_token"]

    # JWT sanity check

    oauth_token.access_token = access_token

    if data.get("refresh_token"):
        oauth_token.refresh_token = data["refresh_token"]

    oauth_token.expires_at = (
        timezone.now()
        + timedelta(
            seconds=data.get("expires_in", 3600)
        )
    )

    oauth_token.is_active = True

    oauth_token.save()

    return oauth_token.access_token


def get_microsoft_access_token(user):

    oauth_token = OAuthToken.objects.filter(
        user=user,
        provider="microsoft",
        is_active=True,
    ).first()

    if not oauth_token:
        raise Exception(
            "Microsoft account not connected."
        )

    enforce_oauth_execution_policy(
        token=oauth_token,
        provider="microsoft",
    )

    if oauth_token.expires_at <= timezone.now():

        refresh_microsoft_token(
            oauth_token
        )

    access_token = oauth_token.access_token

    if not access_token:

        raise Exception(
            "Microsoft access token missing."
        )

    return access_token