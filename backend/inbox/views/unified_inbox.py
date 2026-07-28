from django.core.paginator import Paginator
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Q

from inbox.models import InboxMessage, Conversation
from inbox.serializers import InboxMessageSerializer


class UnifiedInboxAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        search = request.GET.get("search")
        platform = request.GET.get("platform")
        unread_only = request.GET.get("unread")
        starred_only = request.GET.get("starred")
        priority_only = request.GET.get("priority")
        page = request.GET.get("page", 1)
        folder = request.GET.get("folder")

        queryset = InboxMessage.objects.filter(
            user=request.user
        )

        # 🔎 Filters
        if search:
            search = search.strip()
            queryset = queryset.filter(
                Q(subject__icontains=search) |
                Q(sender__icontains=search) |
                Q(body__icontains=search)
            ).distinct()

        if search:
            queryset = queryset.order_by("-received_at")

        if platform:
            queryset = queryset.filter(platform=platform)

        if unread_only == "true":
            queryset = queryset.filter(is_read=False)

        if starred_only == "true":
            queryset = queryset.filter(is_starred=True)

        if priority_only == "true":
            queryset = queryset.filter(is_priority=True)

        if folder:
            queryset = queryset.filter(folder=folder)

        # 🧠 Smart Ordering
        queryset = queryset.order_by(
            "-priority_score",
            "-is_starred",
            "-received_at"
        )

        # 📄 Pagination
        paginator_obj = Paginator(queryset, 20)
        page_obj = paginator_obj.get_page(page)

        serializer = InboxMessageSerializer(page_obj, many=True)

        return Response({
            "count": paginator_obj.count,
            "total_pages": paginator_obj.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data
        }, status=status.HTTP_200_OK)

class UnifiedConversationInboxAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            user = request.user
            folder = request.GET.get("folder", "inbox")
            search = (request.GET.get("search") or "").strip()
            platform = (request.GET.get("platform") or "").strip()
            account_id = request.GET.get("account_id")
            unread_only = request.GET.get("unread")
            starred_only = request.GET.get("starred")
            page = request.GET.get("page", 1)
            page_size = min(int(request.GET.get("page_size", 30) or 30), 100)

            conversations = Conversation.objects.filter(user=user)

            if folder == "sent":
                conversations = conversations.filter(
                    messages__direction="outbound"
                ).distinct()

            elif folder == "draft":
                conversations = conversations.filter(
                    messages__is_draft=True
                ).distinct()

            else:
                conversations = conversations.filter(
                    messages__direction="inbound"
                ).distinct()

            if search:
                conversations = conversations.filter(
                    Q(subject__icontains=search)
                    | Q(last_message_preview__icontains=search)
                    | Q(messages__subject__icontains=search)
                    | Q(messages__sender__icontains=search)
                    | Q(messages__body__icontains=search)
                ).distinct()

            if platform:
                conversations = conversations.filter(
                    Q(email_account__account_type=platform)
                    | Q(messages__platform=platform)
                ).distinct()

            if account_id:
                conversations = conversations.filter(email_account_id=account_id)

            if unread_only == "true":
                conversations = conversations.filter(
                    Q(unread_count__gt=0) | Q(messages__is_read=False)
                ).distinct()

            if starred_only == "true":
                conversations = conversations.filter(
                    Q(is_starred=True) | Q(messages__is_starred=True)
                ).distinct()

            conversations = (
                conversations.select_related("last_message", "email_account")
                .annotate(latest_message_at=Max("messages__received_at"))
                .order_by("-last_message_at", "-latest_message_at", "-created_at")
                .distinct()
            )

            paginator_obj = Paginator(conversations, page_size)
            page_obj = paginator_obj.get_page(page)

            results = []

            for conv in page_obj:

                last = conv.last_message if conv.last_message else None
                if last is None:
                    last = (
                        conv.messages.filter(user=user)
                        .order_by("-received_at")
                        .first()
                    )

                subject = (
                    last.subject
                    if last and last.subject
                    else conv.subject or "No Subject"
                )
                preview = (
                    last.body[:120]
                    if last and last.body
                    else conv.last_message_preview or ""
                )
                platform_value = (
                    conv.email_account.account_type
                    if conv.email_account
                    else last.platform if last else ""
                )
                last_message_time = (
                    conv.last_message_at
                    or getattr(conv, "latest_message_at", None)
                    or (last.received_at if last else None)
                )

                results.append({
                    "conversation_id": conv.id,
                    "subject": subject,
                    "preview": preview,
                    "platform": platform_value,
                    "last_message_time": last_message_time,
                    "unread_count": getattr(conv, "unread_count", 0),
                    "is_starred": getattr(conv, "is_starred", False),
                    "email_account_id": conv.email_account_id,
                })

            return Response({
                "count": paginator_obj.count,
                "total_pages": paginator_obj.num_pages,
                "current_page": page_obj.number,
                "results": results,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
