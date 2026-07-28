from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from oauth_tokens.models import OAuthToken
from audit_logs.models import AuditLog


def safe_audit_log(**data):
    """
    Create AuditLog safely by only passing fields
    that actually exist on the model.
    """
    valid_fields = {f.name for f in AuditLog._meta.fields}
    clean_data = {k: v for k, v in data.items() if k in valid_fields}
    if clean_data:
        AuditLog.objects.create(**clean_data)


class AdminDisableOAuthAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, token_id):
        token = OAuthToken.objects.get(id=token_id)

        token.disabled_by_admin = True
        token.disabled_reason = request.data.get(
            "reason", "Disabled by admin"
        )
        token.save()

        safe_audit_log(
            user=request.user,
            action="OAUTH_DISABLED",
        )

        return Response({"status": "OAuth access disabled"})


class AdminEnableOAuthAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, token_id):
        token = OAuthToken.objects.get(id=token_id)

        token.disabled_by_admin = False
        token.disabled_reason = None
        token.save()

        safe_audit_log(
            user=request.user,
            action="OAUTH_ENABLED",
        )

        return Response({"status": "OAuth access enabled"})
