from rest_framework import serializers
from inbox.models import Conversation
from inbox.models import InboxMessage


class InboxMessageSerializer(serializers.ModelSerializer):
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
        ]


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "subject",
            "participants",
            "updated_at",
            "last_message",
        ]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-received_at").first()
        return msg.body[:120] if msg else None


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = InboxMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "subject",
            "participants",
            "messages",
        ]
