import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from oauth_tokens.models import OAuthToken


def refresh_google_token(oauth_token: OAuthToken):
    """
    Refresh Google OAuth access token silently.
    """

    if not oauth_token.refresh_token:
        raise ValueError("No refresh token available")

    data = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'refresh_token': oauth_token.refresh_token,
        'grant_type': 'refresh_token',
    }

    response = requests.post(
        'https://oauth2.googleapis.com/token',
        data=data
    )

    if response.status_code != 200:
        raise ValueError("Failed to refresh Google token")

    token_data = response.json()

    oauth_token.access_token = token_data['access_token']
    oauth_token.expires_at = timezone.now() + timedelta(
        seconds=token_data.get('expires_in', 3600)
    )
    oauth_token.save(update_fields=['access_token', 'expires_at'])

    return oauth_token

def refresh_microsoft_token(oauth_token: OAuthToken):
    """
    Refresh Microsoft OAuth access token silently.
    """

    data = {
        'client_id': settings.MICROSOFT_CLIENT_ID,
        'client_secret': settings.MICROSOFT_CLIENT_SECRET,
        'refresh_token': oauth_token.refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/.default',
    }

    response = requests.post(
        'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        data=data
    )

    if response.status_code != 200:
        raise ValueError("Failed to refresh Microsoft token")

    token_data = response.json()

    oauth_token.access_token = token_data['access_token']
    oauth_token.expires_at = timezone.now() + timedelta(
        seconds=token_data.get('expires_in', 3600)
    )
    oauth_token.save(update_fields=['access_token', 'expires_at'])

    return oauth_token
