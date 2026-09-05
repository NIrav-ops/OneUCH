import requests
import email
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.response import Response

from oauth_tokens.models import OAuthToken

from rest_framework.permissions import AllowAny

from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from googleapiclient.discovery import build

from googleapis.utils import get_gmail_credentials
from timeline.services import create_timeline_event

from knowledge.services.message_processor import MessageProcessor

from email_accounts.models import EmailAccount
from inbox.services.sync_status import update_sync_status



class GmailConversationPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        credentials = get_gmail_credentials(user)
        service = build("gmail", "v1", credentials=credentials)

        results = service.users().threads().list(
            userId="me",
            maxResults=20,
        ).execute()

        threads = results.get("threads", [])

        response_data = []

        for thread in threads:
            thread_id = thread["id"]

            thread_data = service.users().threads().get(
                userId="me",
                id=thread_id,
                format="metadata",
                metadataHeaders=["Subject"]
            ).execute()

            messages = thread_data.get("messages", [])
            if not messages:
                continue

            latest_message = messages[-1]

            subject = ""
            for header in latest_message["payload"]["headers"]:
                if header["name"] == "Subject":
                    subject = header["value"]
                    break

            snippet = thread_data.get("snippet", "")

            internal_date = int(latest_message["internalDate"]) / 1000
            last_message_date = datetime.fromtimestamp(internal_date)

            unread = "UNREAD" in latest_message.get("labelIds", [])

            response_data.append({
                "conversation_id": thread_id,
                "subject": subject,
                "snippet": snippet,
                "last_message_date": last_message_date,
                "unread": unread,
                "platform": "gmail",
            })

        return Response(response_data)

class GmailBulkActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        {
            "conversation_ids": ["188d9c33", "188abc44"],
            "action": "mark_read"  // mark_read | delete | archive
        }
        """

        user = request.user
        conversation_ids = request.data.get("conversation_ids", [])
        action = request.data.get("action")

        credentials = get_gmail_credentials(user)
        service = build("gmail", "v1", credentials=credentials)

        for thread_id in conversation_ids:
            if action == "mark_read":
                service.users().threads().modify(
                    userId="me",
                    id=thread_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()

            elif action == "archive":
                service.users().threads().modify(
                    userId="me",
                    id=thread_id,
                    body={"removeLabelIds": ["INBOX"]}
                ).execute()

            elif action == "delete":
                service.users().threads().trash(
                    userId="me",
                    id=thread_id
                ).execute()

        return Response({"status": "success"})
    
from datetime import datetime
import time
from django.utils import timezone
from django.db import transaction
from googleapiclient.discovery import build
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Conversation, InboxMessage, InboxSyncStatus, User
from googleapis.utils import get_gmail_credentials


class GmailSyncAPIView(APIView):
    """
    Queue the governed Gmail mailbox synchronization task.

    A 90-day Gmail backfill may require many provider requests,
    so provider traversal must not execute inside the HTTP
    request/response lifecycle.
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
                account_type="gmail",
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
                            "No active Gmail "
                            "account is connected."
                        ),
                },
                status=400,
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
                            "Unable to start Gmail "
                            "synchronization."
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
                    "gmail",

                "email_account_id":
                    email_account.id,

                "message":
                    (
                        "Gmail synchronization started."
                    ),
            },
            status=202,
        )

from rest_framework import status

class GmailMarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message_id = request.data.get("message_id")

        if not message_id:
            return Response(
                {"error": "message_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            message = InboxMessage.objects.get(
                id=message_id,
                user=request.user,
                platform="gmail"
            )

            credentials = get_gmail_credentials(request.user)
            service = build("gmail", "v1", credentials=credentials)

            # Remove UNREAD label in Gmail
            service.users().messages().modify(
                userId="me",
                id=message.external_message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            # Update DB
            message.is_read = True
            message.save(update_fields=["is_read"])

            return Response({"status": "marked_read"})

        except InboxMessage.DoesNotExist:
            return Response(
                {"error": "Message not found"},
                status=status.HTTP_404_NOT_FOUND
            )
from rest_framework import status


class GmailBulkConversationActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conversation_ids = request.data.get("conversation_ids", [])
        action = request.data.get("action")

        if not conversation_ids or not action:
            return Response(
                {"error": "conversation_ids and action required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credentials = get_gmail_credentials(request.user)
        service = build("gmail", "v1", credentials=credentials)

        updated = 0

        for conv_id in conversation_ids:

            messages = InboxMessage.objects.filter(
                conversation__id=conv_id,
                user=request.user,
                platform="gmail",
            )

            for message in messages:

                if action == "mark_read":
                    service.users().messages().modify(
                        userId="me",
                        id=message.external_message_id,
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                    message.is_read = True

                elif action == "mark_unread":
                    service.users().messages().modify(
                        userId="me",
                        id=message.external_message_id,
                        body={"addLabelIds": ["UNREAD"]},
                    ).execute()

                    message.is_read = False

                elif action == "archive":
                    service.users().messages().modify(
                        userId="me",
                        id=message.external_message_id,
                        body={"removeLabelIds": ["INBOX"]},
                    ).execute()

                elif action == "delete":
                    service.users().messages().trash(
                        userId="me",
                        id=message.external_message_id,
                    ).execute()

                message.save(update_fields=["is_read"])
                updated += 1

        return Response({
            "status": "bulk_action_complete",
            "updated_messages": updated,
        })

from urllib.parse import urlencode
from django.conf import settings
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from accounts.authentication import (
    OneUCHJWTAuthentication,
    get_active_membership,
)

from oauth_tokens.oauth_state import (
    OAuthStateError,
    create_oauth_state,
    resolve_oauth_state,
)

@api_view(["GET"])
@authentication_classes([OneUCHJWTAuthentication])
@permission_classes([IsAuthenticated])
def google_oauth_start(request):

    state = create_oauth_state(
        user_id=request.user.id,
        provider="google",
    )

    base_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": (
            "https://www.googleapis.com/auth/gmail.modify "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/userinfo.email"
        ),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    url = f"{base_url}?{urlencode(params)}"

    return JsonResponse(
        {
            "authorization_url": url,
            "provider": "google",
        },
        status=200,
    )

import requests
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from oauth_tokens.models import OAuthToken
from django.contrib.auth import get_user_model


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def google_oauth_callback(request):

    code = request.GET.get("code")
    state = request.GET.get("state")

    if not code:
        return JsonResponse(
            {
                "error": "Missing authorization code",
            },
            status=400,
        )

    try:
        state_data = resolve_oauth_state(
            state=state,
            provider="google",
        )

    except OAuthStateError as exc:
        return JsonResponse(
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
        return JsonResponse(
            {
                "error": "OAuth user is unavailable",
            },
            status=400,
        )

    # OAuth callback state identifies a user,
    # but that user must still belong to an
    # active One UCH workspace before any
    # provider token exchange occurs.

    if get_active_membership(
        user
    ) is None:
        return JsonResponse(
            {
                "error": "OAuth user is unavailable",
            },
            status=400,
        )

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    # KEEP THE REMAINDER OF YOUR EXISTING CALLBACK
    # FROM THE requests.post(...) SECTION ONWARD.

    response = requests.post(token_url, data=data)
    token_data = response.json()

    if "access_token" not in token_data:
        return JsonResponse(
            {
                "error": "Invalid OAuth response",
            },
            status=400,
        )

    # 🔥 FIX: expires_at
    expires_in = token_data.get("expires_in", 3600)
    expires_at = timezone.now() + timedelta(seconds=expires_in)

    OAuthToken.objects.update_or_create(
        user=user,  # ⚠️ TEMP (later dynamic)
        provider="google",
        defaults={
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,   # ✅ FIXED
            "is_active": True,
        }
    )
    # Get Gmail email address

    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={
            "Authorization": f"Bearer {token_data['access_token']}"
        }
    ).json()

    email = userinfo.get("email")

    if email:

        from email_accounts.models import EmailAccount

        EmailAccount.objects.update_or_create(
            user=user,
            email_address=email,
            defaults={
                "account_type": "gmail",
                "is_active": True,
            }
        )

    return JsonResponse({"status": "Gmail connected successfully"})
