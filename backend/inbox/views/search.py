from rest_framework.views import APIView
from rest_framework.response import Response
from inbox.models import InboxMessage

class MessageSearchAPIView(APIView):

    def get(self, request):

        query = request.GET.get("q", "")

        messages = InboxMessage.objects.filter(
            user=request.user,
            subject__icontains=query
        ).order_by("-received_at")[:50]

        data = [
            {
                "subject": m.subject,
                "sender": m.sender,
                "received_at": m.received_at
            }
            for m in messages
        ]

        return Response(data)