import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from oauth_tokens.models import OAuthToken
from oauth_tokens.policy import enforce_oauth_execution_policy
from microsoftapis.utils import refresh_microsoft_token


def refresh_google_token(token: OAuthToken):
    """
    Refresh Google OAuth access token using refresh token
    """
    enforce_oauth_execution_policy(
        token=token,
        provider="google",
    )

    if not token.refresh_token:
        raise Exception("Google refresh token missing. Please reconnect Gmail.")

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": token.refresh_token,
            "grant_type": "refresh_token",
        },
    ).json()

    if "access_token" not in response:
        raise Exception(f"Failed to refresh Google token: {response}")

    token.access_token = response["access_token"]
    token.expires_at = timezone.now() + timedelta(
        seconds=response.get("expires_in", 3600)
    )
    token.save()

    return token


def get_valid_oauth_token(user, provider: str):
    """
    Returns a valid OAuth access token for the given user & provider.
    Auto-refreshes token if expired.
    """

    if not user:
        raise Exception("User not provided while fetching OAuth token")

    if provider not in ["google", "microsoft"]:
        raise Exception(f"Unsupported OAuth provider: {provider}")

    token = OAuthToken.objects.filter(
        user=user,
        provider=provider,
        is_active=True
    ).first()

    if not token:
        raise Exception(
            f"{provider.title()} account not connected. Please connect {provider} first."
        )
    
    enforce_oauth_execution_policy(
        token=token,
        provider=provider,
    )

    if token.is_expired():

        if provider == "google":

            token = refresh_google_token(
                token
            )

        elif provider == "microsoft":

            refresh_microsoft_token(
                token
            )

    return token
