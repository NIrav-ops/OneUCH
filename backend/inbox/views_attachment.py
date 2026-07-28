from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.conf import settings
from oauth_tokens.models import OAuthToken
from inbox.models import InboxMessage
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from urllib.parse import quote
import base64
import requests


class DownloadAttachmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _build_response(self, file_data, filename, content_type):
        response = HttpResponse(
            file_data,
            content_type=content_type or "application/octet-stream",
        )
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(filename)}"
        )
        response["Content-Length"] = str(len(file_data))
        return response

    def _find_attachment_meta(self, message, attachment_id):
        for item in (message.attachment_meta or []):
            if item.get("attachment_id") == attachment_id:
                return item
        return None

    def get(self, request, message_id, attachment_id):
        try:
            message = InboxMessage.objects.filter(
                id=message_id,
                user=request.user
            ).first()

            if not message:
                return HttpResponse("Message not found", status=404)

            filename = "attachment"
            content_type = "application/octet-stream"

            # =========================
            # GMAIL
            # =========================
            if message.platform == "gmail":
                token = OAuthToken.objects.filter(
                    user=request.user,
                    provider="google",
                    is_active=True
                ).first()

                if not token:
                    return HttpResponse("No Google token", status=400)

                creds = Credentials(
                    token=token.access_token,
                    refresh_token=token.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                    scopes=["https://www.googleapis.com/auth/gmail.modify"],
                )

                service = build("gmail", "v1", credentials=creds)

                att = service.users().messages().attachments().get(
                    userId="me",
                    messageId=message.external_message_id,
                    id=attachment_id
                ).execute()

                file_data = base64.urlsafe_b64decode(att["data"].encode("UTF-8"))

                meta = self._find_attachment_meta(message, attachment_id)
                if meta:
                    filename = meta.get("filename", filename)
                    content_type = meta.get("mime_type", content_type)

                return self._build_response(file_data, filename, content_type)

            # =========================
            # OUTLOOK
            # =========================
            if message.platform == "outlook":
                token = OAuthToken.objects.filter(
                    user=request.user,
                    provider="microsoft",
                    is_active=True
                ).first()

                if not token:
                    return HttpResponse("No Microsoft token", status=400)

                headers = {
                    "Authorization": f"Bearer {token.access_token}"
                }

                att_resp = requests.get(
                    f"https://graph.microsoft.com/v1.0/me/messages/{message.external_message_id}/attachments/{attachment_id}",
                    headers=headers
                )

                if att_resp.status_code != 200:
                    return HttpResponse(att_resp.text, status=att_resp.status_code)

                att_json = att_resp.json()

                filename = att_json.get("name", filename)
                content_type = att_json.get("contentType", content_type)
                content_b64 = att_json.get("contentBytes")

                if not content_b64:
                    return HttpResponse("Attachment content missing", status=500)

                file_data = base64.b64decode(content_b64)

                return self._build_response(file_data, filename, content_type)

            return HttpResponse("Unsupported platform", status=400)

        except Exception as e:
            print("DOWNLOAD ERROR:", str(e))
            return HttpResponse(str(e), status=500)