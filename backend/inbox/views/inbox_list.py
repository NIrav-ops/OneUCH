from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from inbox.models import InboxMessage
from inbox.serializers import InboxMessageSerializer
from inbox.services.smart_ai import analyze_email

from platform_core.api.tenant import (
    get_user_organization_or_404,
)

class InboxListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        query = request.query_params.get("q")
        unread = request.query_params.get("unread")
        tag = request.query_params.get("tag")
        sort = request.query_params.get("sort")

        qs = InboxMessage.objects.filter(
            user=user,
            organization=organization,
        )

        platform = request.query_params.get("platform")

        if platform:
            qs = qs.filter(platform=platform)


        # 🔍 Search
        if query:
            qs = qs.filter(
                Q(subject__icontains=query)
                | Q(sender__icontains=query)
                | Q(body__icontains=query)
            )

        # 📬 Unread filter
        if unread == "true":
            qs = qs.filter(is_read=False)

        messages = list(qs)

        enriched = []

        for msg in messages:
            analysis = analyze_email(msg.subject or "", msg.body or "")
            enriched.append((msg, analysis))

        # 🏷 Tag filter
        if tag:
            enriched = [
                item for item in enriched
                if tag in item[1]["tags"]
            ]

        # 📊 Sorting
        if sort == "priority":
            enriched.sort(
                key=lambda x: x[1]["priority_score"],
                reverse=True,
            )

        elif sort == "unread_first":
            enriched.sort(
                key=lambda x: x[0].is_read
            )

        else:
            enriched.sort(
                key=lambda x: x[0].received_at,
                reverse=True,
            )

        sorted_messages = [item[0] for item in enriched]

        serializer = InboxMessageSerializer(sorted_messages, many=True)

        return Response(serializer.data)
