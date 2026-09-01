import requests
from datetime import timedelta, datetime
from django.shortcuts import redirect
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from inbox.models import Conversation, InboxMessage, InboxSyncStatus
from microsoftapis.utils import get_microsoft_access_token
from oauth_tokens.models import OAuthToken
from django.utils.timezone import make_naive
from datetime import timezone as dt_timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import urllib.parse
from timeline.services import create_timeline_event
from knowledge.services.message_processor import MessageProcessor
from oauth_tokens.oauth_state import (OAuthStateError,create_oauth_state,resolve_oauth_state,)


class MicrosoftOAuthStart(APIView):


    authentication_classes = [
        JWTAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        state = create_oauth_state(
            user_id=request.user.id,
            provider="microsoft",
        )

        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "response_mode": "query",
            "scope": "offline_access Mail.ReadWrite Mail.Send User.Read",
            "state": state,
        }

        auth_url = (
            "https://login.microsoftonline.com/"
            "common/oauth2/v2.0/authorize?"
            + urllib.parse.urlencode(params)
        )

        return Response(
        {
            "authorization_url": auth_url,
            "provider": "microsoft",
        },
        status=200,
    )

from django.contrib.auth import get_user_model
from email_accounts.models import EmailAccount

class MicrosoftOAuthCallback(APIView):

    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    def get(self, request):

        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code:
            return Response(
                {
                    "error": "Missing authorization code",
                },
                status=400,
            )

        try:
            state_data = resolve_oauth_state(
                state=state,
                provider="microsoft",
            )

        except OAuthStateError as exc:
            return Response(
                {
                    "error": str(exc),
                },
                status=400,
            )

        User = get_user_model()

        try:
            user = User.objects.get(
                id=state_data["user_id"],
                is_active=True,
            )

        except User.DoesNotExist:
            return Response(
                {
                    "error": "OAuth user is unavailable",
                },
                status=400,
            )

        token_response = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        ).json()

        OAuthToken.objects.update_or_create(
            user=user,
            provider="microsoft",
            defaults={
                "access_token": token_response["access_token"],
                "refresh_token": token_response.get("refresh_token"),
                "expires_at": timezone.now()
                + timedelta(seconds=token_response.get("expires_in", 3600)),
                "is_active": True,
            },
        )

        # 🔥 Get user email from Graph
        headers = {
            "Authorization": f"Bearer {token_response['access_token']}"
        }

        profile_response = requests.get(
            "https://graph.microsoft.com/v1.0/me?$select=mail,userPrincipalName,displayName",
            headers=headers,
        )

        profile_data = profile_response.json()
        print("MICROSOFT PROFILE:", profile_data)
        email_address = profile_data.get("mail") or profile_data.get("userPrincipalName")

        if not email_address:
            return Response(
                {"error": "Could not fetch email address from Microsoft"},
                status=400,
    )
       

        EmailAccount.objects.update_or_create(
            user=user,
            email_address=email_address,
            defaults={
                "account_type": "outlook",
                "is_active": True,
            },
        )

        return Response({"status": "Microsoft account connected successfully"})


class OutlookSyncAPIView(APIView):
    """
    Queue the governed Microsoft mailbox synchronization task.

    The provider traversal itself runs in Celery so initial
    historical synchronization cannot hold an HTTP request open.
    """

    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):

        from email_accounts.models import (
            EmailAccount,
        )

        from inbox.tasks import (
            sync_email_account,
        )


        email_account = (
            EmailAccount.objects
            .filter(
                user=request.user,
                account_type="outlook",
                is_active=True,
            )
            .order_by(
                "-id"
            )
            .first()
        )


        if email_account is None:

            return Response(
                {
                    "status":
                        "no_mailbox",

                    "error":
                        (
                            "No active Outlook "
                            "account found."
                        ),
                },
                status=404,
            )


        try:

            sync_email_account.delay(
                email_account.id
            )


        except Exception:

            return Response(
                {
                    "status":
                        "queue_failed",

                    "error":
                        (
                            "Unable to start Microsoft "
                            "mailbox synchronization."
                        ),

                    "action":
                        (
                            "Try again shortly. If the "
                            "problem continues, contact "
                            "your One UCH administrator."
                        ),
                },
                status=503,
            )


        return Response(
            {
                "status":
                    "sync_queued",

                "provider":
                    "outlook",

                "email_account_id":
                    email_account.id,

                "message":
                    (
                        "Microsoft mailbox "
                        "synchronization started."
                    ),
            },
            status=202,
        )
