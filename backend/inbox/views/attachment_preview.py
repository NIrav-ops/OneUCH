from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Attachment, AttachmentAccessLog, UsageEvent
from inbox.audit import log_audit_event
from inbox.billing.utils import check_usage_limit, UsageLimitExceeded


class AttachmentPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        user = request.user

        # 1️⃣ Fetch attachment
        try:
            attachment = Attachment.objects.select_related(
                "message",
                "message__organization",
            ).get(id=attachment_id)
        except Attachment.DoesNotExist:
            raise Http404("Attachment not found")

        # 2️⃣ Org ownership check
        membership = getattr(user, "organization_membership", None)
        if not membership:
            raise Http404("Attachment not found")

        if attachment.message.organization != membership.organization:
            raise Http404("Attachment not found")

        # 3️⃣ Policy enforcement
        policy = membership.organization.attachment_policy
        if not policy or not policy.allow_preview:
            return Response(
                {"error": "Preview blocked by policy"},
                status=403,
            )

        # 4️⃣ 🔥 BILLING USAGE ENFORCEMENT (THIS WAS MISSING)
        try:
            check_usage_limit(
                organization=membership.organization,
                event_type="ATTACHMENT_PREVIEW",
            )
        except UsageLimitExceeded as e:
            return Response(
                {"error": str(e)},
                status=403,
            )

        # 5️⃣ Audit log
        log_audit_event(
            user=user,
            organization=membership.organization,
            action="ATTACHMENT_PREVIEW",
            request=request,
            metadata={
                "attachment_id": attachment.id,
                "filename": attachment.filename,
            },
        )

        # 6️⃣ Access log
        AttachmentAccessLog.objects.create(
            attachment=attachment,
            user=user,
            action="preview",
            scan_status="clean",
        )

        # 7️⃣ Usage event
        UsageEvent.objects.create(
            organization=membership.organization,
            user=user,
            event_type="ATTACHMENT_PREVIEW",
            metadata={
                "attachment_id": attachment.id,
            },
        )

        # 8️⃣ Serve preview
        return FileResponse(
            as_attachment=False,
            filename=attachment.filename,
            content_type=attachment.content_type,
        )
