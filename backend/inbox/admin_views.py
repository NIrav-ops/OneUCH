from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from inbox.audit import log_audit_event

from inbox.permissions import IsOrganizationAdmin


class UpdateAttachmentPolicyAPIView(APIView):
    """
    Update attachment policy for the current organization (org-admin only)
    """
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def patch(self, request):
        # 1️⃣ Get organization from user membership
        membership = getattr(request.user, "organization_membership", None)
        if not membership:
            return Response(
                {"error": "User is not associated with any organization"},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = membership.organization
        policy = org.attachment_policy

        if not policy:
            return Response(
                {"error": "No attachment policy assigned to organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2️⃣ Update allowed fields only
        allowed_fields = [
            "max_size_mb",
            "allow_preview",
            "allow_download",
        ]

        updated = False
        for field in allowed_fields:
            if field in request.data:
                setattr(policy, field, request.data[field])
                updated = True

        if not updated:
            return Response(
                {"error": "No valid fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        policy.save()

        log_audit_event(
            user=request.user,
            organization=org,
            action="ATTACHMENT_POLICY_UPDATE",
            request=request,
            metadata={
                "updated_fields": list(request.data.keys()),
    },
)

        return Response(
            {
                "status": "updated",
                "organization": org.name,
                "policy": {
                    "id": policy.id,
                    "name": policy.name,
                    "max_size_mb": policy.max_size_mb,
                    "allow_preview": policy.allow_preview,
                    "allow_download": policy.allow_download,
                },
            },
            status=status.HTTP_200_OK,
        )
