from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxSyncStatus


class InboxSyncStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = InboxSyncStatus.objects.filter(user=request.user)

        data = [
            {
                "platform": s.platform,
                "status": s.status,
                "progress": s.progress,
                "last_synced_at": s.last_synced_at,
                "error_message": s.error_message,
            }
            for s in qs
        ]

        return Response(data)
