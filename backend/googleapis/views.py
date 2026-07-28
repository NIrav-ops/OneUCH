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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("🚀 NEW GMAIL SYNC API HIT")

        user = request.user
        organization = user.organization_membership.organization

# ---------------------------------------------------------
# Enterprise OAuth Handling
# ---------------------------------------------------------

        try:

            credentials = get_gmail_credentials(user)

            service = build(
                "gmail",
                "v1",
            credentials=credentials,
            )

        except Exception as exc:

            print("❌ Gmail OAuth Error:", exc)

        return Response(
            {
                "status": "oauth_failed",
                "message": str(exc),
                "action": "Reconnect Gmail account",
            },
            status=401,
        )

        results = service.users().messages().list(
            userId="me",
            maxResults=50,
            q="in:inbox OR in:sent"
        ).execute()

        print("📊 RAW LIST RESPONSE:", results)
        messages = results.get("messages",[])
        print("📊 MESSAGES FOUND:", len(messages))
        

        for m in messages:

            msg = service.users().messages().get(
                userId="me",
                id=m["id"],
                format="full",
                metadataHeaders=["Subject", "From", "To"],
            ).execute()

            print("FULL MESSAGE RAW ↓↓↓")
            print(msg)
            print("HEADERS ↓↓↓")
            print(msg.get("payload", {}).get("headers"))

            # -------------------------
            # SUBJECT + SENDER EXTRACTION (FINAL FIX)
            # -------------------------

            subject = None
            sender = ""
            recipients = ""

            headers = msg.get("payload", {}).get("headers", [])   # ✅ THIS FIXES YELLOW LINE

            for h in headers:
                name = h.get("name", "").lower()   # ✅ case-insensitive
                value = h.get("value", "")

                if name == "subject":
                    subject = value

                elif name == "from":
                    sender = value

                elif name == "to":
                    recipients = value

            # -------------------------
            # FALLBACK (IMPORTANT)
            # -------------------------

            if not subject:
                subject = msg.get("snippet")   # ✅ Gmail always gives snippet

            if not subject:
                subject = "No Subject"
            # -------------------------
            # DEBUG (YOU ASKED WHERE TO SEE IT)
            # -------------------------

            print("🔥 EXTRACTED SUBJECT:", subject)    

            # ✅ CREATE CONVERSATION (1 thread = 1 conversation)
            thread_id = msg.get("threadId") or m.get("id")

            conversation_key = f"gmail_{thread_id}"

            conversation, _ = Conversation.objects.get_or_create(
                user=user,
                conversation_key=conversation_key,
                defaults={
                    "organization": organization,
                    "subject": subject
                }
            )

            # ✅ SAVE MESSAGE (NO DUPLICATE)
            if InboxMessage.objects.filter(
                external_message_id=msg["id"]
            ).exists():
                continue

            message_obj = InboxMessage.objects.create(
                user=user,
                organization=organization,
                conversation=conversation,
                platform="gmail",
                direction="inbound",
                external_message_id=msg["id"],
                external_conversation_id=thread_id,
                sender=sender,
                recipients=recipients,
                subject=subject,
                body=msg.get("snippet", ""),
                received_at=timezone.now(),
                is_read="UNREAD" not in msg.get("labelIds", []),
            )

            print("TIMELINE GMAIL EVENT",conversation.id)

            create_timeline_event(
                conversation=conversation,
                event_type="message_received",
                title="New email received",
                details={
                    "platform":"gmail",
                    "sender":msg.get("sender"),
                    "subject":msg.get("subject"),
                },
                event_at=message_obj.received_at,
            )

            # ✅ UPDATE CONVERSATION (ONLY IF SUBJECT VALID)
            if subject and subject.strip().lower() != "no subject":
                conversation.subject = subject

            conversation.last_message = message_obj
            conversation.last_message_at = message_obj.received_at

            conversation.save()

            # ---------------------------------------------------------
            # Enterprise Knowledge Processing
            # ---------------------------------------------------------

            try:

                processor = MessageProcessor()

                processor.process_message(
                    organization=organization,
                    message=message_obj,
                    sender=sender,
                    subject=subject,
                    body=msg.get("snippet", ""),
                    source_channel="gmail",
                )

            except Exception as exc:

                print(
                    "Knowledge Processing Error:",
                    exc,
                )

        return Response({"status": "gmail sync complete"})

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
from django.http import HttpResponseRedirect
from django.conf import settings

def google_oauth_start(request):

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

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
        "state": request.user.id if request.user.is_authenticated else "1",
    }

    url = f"{base_url}?{urlencode(params)}"

    return HttpResponseRedirect(url)

import requests
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from oauth_tokens.models import OAuthToken
from django.contrib.auth import get_user_model


def google_oauth_callback(request):

    code = request.GET.get("code")
    state = request.GET.get("state")

    if not state:
        return JsonResponse(
            {"error": "Missing state"},
            status=400
        )

    User = get_user_model()

    try:
        user = User.objects.get(id=state)
    except User.DoesNotExist:
        return JsonResponse(
            {"error": "Invalid user"},
            status=400
        )

    if not code:
        return JsonResponse({"error": "Missing code"}, status=400)

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=data)
    token_data = response.json()

    if "access_token" not in token_data:
        return JsonResponse({
            "error": "Invalid OAuth response",
            "details": token_data
        }, status=400)

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
