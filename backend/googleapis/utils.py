import requests
from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials

from oauth_tokens.models import OAuthToken
from oauth_tokens.policy import enforce_oauth_execution_policy


def refresh_google_token(oauth_token):
    """
    Refresh expired Google access token
    """

    enforce_oauth_execution_policy(
        token=oauth_token,
        provider="google",
    )

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": oauth_token.refresh_token,
            "grant_type": "refresh_token",
        },
    ).json()

    if "access_token" not in response:
        raise Exception(f"Google refresh failed: {response}")

    oauth_token.access_token = response["access_token"]
    oauth_token.expires_at = timezone.now() + timezone.timedelta(
        seconds=response.get("expires_in", 3600)
    )
    oauth_token.save()

    return oauth_token.access_token


def get_gmail_credentials(user):
    """
    Returns valid Google Credentials object
    Auto refreshes if expired
    """

    oauth_token = OAuthToken.objects.filter(
        user=user,
        provider="google",
        is_active=True
    ).first()

    if not oauth_token:
        raise Exception("Google account not connected")

    enforce_oauth_execution_policy(
        token=oauth_token,
        provider="google",
    )

    # Refresh if expired
    if oauth_token.expires_at <= timezone.now():
        refresh_google_token(oauth_token)

    credentials = Credentials(
        token=oauth_token.access_token,
        refresh_token=oauth_token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",],
    )

    return credentials