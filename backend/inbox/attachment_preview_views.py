from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from inbox.models import Attachment, AttachmentAccessLog


PREVIEWABLE_TYPES = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
]


class AttachmentPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = Attachment.objects.filter(
            id=attachment_id,
            message__user=request.user
        ).first()

        if not attachment:
            raise Http404("Attachment not found")

        if attachment.content_type not in PREVIEWABLE_TYPES:
            raise Http404("Preview not allowed")

        # 🔐 LOG ACCESS
        AttachmentAccessLog.objects.create(
            attachment=attachment,
            user=request.user,
            action="preview"
        )

        response = FileResponse(
            content_type=attachment.content_type
        )
        response["Content-Disposition"] = "inline"
        return response
