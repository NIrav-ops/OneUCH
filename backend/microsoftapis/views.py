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


class MicrosoftOAuthStart(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "response_mode": "query",
            "scope": "offline_access Mail.Read User.Read",
            "state": request.user.id if request.user.is_authenticated else "1",
        }

        auth_url = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            + urllib.parse.urlencode(params)
        )

        return redirect(auth_url)

from django.contrib.auth import get_user_model
from email_accounts.models import EmailAccount

class MicrosoftOAuthCallback(APIView):
    permission_classes = [AllowAny]

    def get(self, request):

        code = request.GET.get("code")
        state = request.GET.get("state")  # 🔥 retrieve user id

        if not code or not state:
            return Response({"error": "Missing code or state"}, status=400)

        User = get_user_model()

        try:
            user = User.objects.get(id=state)
        except User.DoesNotExist:
            return Response({"error": "Invalid user"}, status=400)

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
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        organization = user.organization_membership.organization

        sync_status, _ = InboxSyncStatus.objects.get_or_create(
            user=user,
            platform="outlook",
            defaults={"status": "idle"},
        )

        try:
            sync_status.status = "syncing"
            sync_status.progress = 5
            sync_status.save()

            access_token = get_microsoft_access_token(user)

            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            # -----------------------------
            # INCREMENTAL LOGIC
            # -----------------------------
            filter_query = ""

            if sync_status.last_synced_at and InboxMessage.objects.filter(
                user=user,
                platform="outlook"
            ).exists():
                
                buffer_time = sync_status.last_synced_at - timedelta(minutes=2)

                # Ensure UTC
                buffer_time = buffer_time.astimezone(dt_timezone.utc)

                # Remove microseconds
                buffer_time = buffer_time.replace(microsecond=0)

                # Format properly
                iso_time = buffer_time.isoformat().replace("+00:00", "Z")

                filter_query = f"&$filter=receivedDateTime ge {iso_time}"

            url = (
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                f"?$top=50{filter_query}"
            )

            messages = []

            while url:
                response = requests.get(url, headers=headers)
                data = response.json()

                if "value" not in data:
                    raise Exception(f"Graph API Error: {data}")

                messages.extend(data.get("value", []))

        # Microsoft pagination link
                url = data.get("@odata.nextLink")

            created_messages = 0
            created_conversations = 0
            print("TOTAL MICROSOFT MESSAGES:", len(messages))

            for msg in messages:

                external_message_id = msg["id"]
                conversation_id = msg.get("conversationId")

                existing = InboxMessage.objects.filter(
                    external_message_id=external_message_id
                ).first()

                is_read = msg.get("isRead", False)

                if existing:
                    if existing.is_read != is_read:
                        existing.is_read = is_read
                        existing.save(update_fields=["is_read"])
                    continue

                # Create / Get Conversation
                conversation_key = f"outlook_{conversation_id}"

                conversation = Conversation.objects.filter(
                    user=user,
                    conversation_key=conversation_key
                ).first()

                if not conversation:
                    conversation = Conversation.objects.create(
                        user=user,
                        organization=organization,
                        conversation_key=conversation_key,
                        subject=msg.get("subject") or "No Subject",
                    )
                    created_conversations += 1

                received_at = datetime.fromisoformat(
                    msg["receivedDateTime"].replace("Z", "+00:00")
                )
                

                message_obj = InboxMessage.objects.create(
                    user=user,
                    organization=organization,
                    conversation=conversation,
                    platform="outlook",
                    external_message_id=external_message_id,
                    external_conversation_id=conversation_id,
                    folder="inbox",
                    direction="inbound",
                    sender=msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                    recipients="",
                    subject=msg.get("subject") or "",
                    body=msg.get("bodyPreview") or "",
                    received_at=received_at,
                    is_read=is_read,
                )

                # ==========================================================
                # Enterprise Knowledge Processing
                # ==========================================================

                try:

                    processor = MessageProcessor()

                    processor.process_message(
                        organization=organization,
                        message=message_obj,
                        sender=msg.get(
                            "from",
                            {}
                        ).get(
                            "emailAddress",
                            {}
                        ).get(
                            "address",
                            "",
                        ),
                        subject=msg.get("subject") or "",
                        body=msg.get("bodyPreview") or "",
                        source_channel="outlook",
                    )

                    print(
                        "🧠 Outlook Knowledge Processed:",
                        msg.get("subject"),
                    )

                except Exception as exc:

                    print(
                        "❌ Outlook Knowledge Error:",
                    exc,
                )

                created_messages += 1

                print("TIMELINE OUTLOOK EVENT", conversation.id)

                create_timeline_event(
                    conversation=conversation,
                    event_type="message_received",
                    title="New Outlook email received",
                    details={
                        "platform":"outlook",
                        "sender":msg.get(
                            "from",
                            {}
                        ).get(
                            "emailAddress",
                            {}
                        ).get(
                            "address"
                        ),
                        "subject":msg.get("subject"),
                    },
                    event_at=received_at,
                )


            # Safely rebuild Outlook conversation metadata

            conversation_ids = (
                InboxMessage.objects.filter(
                    user=user,
                    platform="outlook",
                )
                .values_list(
                    "conversation_id",
                    flat=True,
                )
                .distinct()
            )

            for conv in Conversation.objects.filter(
                id__in=conversation_ids
            ):

                last_message = (
                    InboxMessage.objects.filter(
                    conversation=conv
                )
                .order_by("-received_at")
                .first()
            )

            conv.last_message = last_message

            conv.last_message_at = (
                last_message.received_at
                if last_message
                else None
            )

            if last_message:
                conv.subject = (
                last_message.subject
                or conv.subject
            )

            conv.save(
                update_fields=[
                    "last_message",
                    "last_message_at",
                    "subject",
                ]
            )

            return Response({
                "status": "outlook_sync_complete",
                "new_conversations": created_conversations,
                "new_messages": created_messages,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            sync_status.status="failed"
            sync_status.error_message=str(e)
            sync_status.save()
            return Response({

                "status":"sync_failed",
                "error":str(e),

            },status=500)