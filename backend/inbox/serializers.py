from rest_framework import serializers
from inbox.models import InboxMessage, Attachment
from inbox.services.smart_ai import analyze_email



# ---------- Attachment ----------
class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            "id",
            "filename",
            "file",
            "size",
            "content_type",
            "uploaded_at",
        ]


# ---------- Inbox LIST (Phase 2.2) ----------
class InboxMessageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxMessage
        fields = [
            "id",
            "platform",
            "direction",
            "sender",
            "recipients",
            "subject",
            "received_at",
            "is_read",
            "created_at",
        ]


# ---------- Inbox DETAIL (Phase 2.4) ----------
class InboxMessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    smart_analysis = serializers.SerializerMethodField()

    class Meta:
        model = InboxMessage
        fields = [
            "id",
            "platform",
            "direction",
            "sender",
            "recipients",
            "subject",
            "body",
            "received_at",
            "is_read",
            "is_starred",
            "attachments",
            "is_priority",
            "priority_score",
            "smart_analysis",
           ]

    def get_smart_analysis(self, obj):
        return analyze_email(obj.subject or "", obj.body or "")

    def get_attachments(self, obj):
        return AttachmentSerializer(
            obj.attachments.all(), many=True
        ).data

class ConversationPreviewSerializer(serializers.Serializer):
    conversation_id = serializers.CharField()
    subject = serializers.CharField()
    snippet = serializers.CharField()
    last_message_date = serializers.DateTimeField()
    unread_count = serializers.IntegerField()
    platform = serializers.CharField()