from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from inbox.audit import log_audit_event

from inbox.models import Attachment, AttachmentAccessLog


class AttachmentDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = (
            Attachment.objects
            .select_related("message", "message__user")
            .filter(id=attachment_id)
            .first()
        )

        if not attachment:
            raise Http404("Attachment does not exist")

        if not attachment.message:
            raise Http404("Attachment not linked to any message")

        if attachment.message.user != request.user:
            raise Http404("You do not have access to this attachment")

        # 🔐 POLICY CHECKS (MUST BE BEFORE RETURN)
        policy = request.user.attachment_policy

        # File existence
        if not attachment.file:
            raise Http404("File not available")

        # Size check (safe even if size missing)
        if attachment.file.size / (1024 * 1024) > policy.max_size_mb:
            raise PermissionDenied("Attachment size exceeds policy limit")

        # Extension check
        ext = attachment.filename.split(".")[-1].lower()
        if policy.allowed_extensions and ext not in policy.allowed_extensions:
            raise PermissionDenied("File type not allowed")
        
        if attachment.scan_status != "clean":
            raise PermissionDenied("Attachment not cleared by security scan")

        # Download allowed?
        if not policy.allow_download:
            raise PermissionDenied("Downloads disabled by admin")

        # ✅ LOG ACCESS
        AttachmentAccessLog.objects.create(
            attachment=attachment,
            user=request.user,
            action="download"
        )

        # ✅ FINALLY RETURN FILE
        return FileResponse(
            as_attachment=True,
            filename=attachment.filename
        )

