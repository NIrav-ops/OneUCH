from rest_framework import serializers
from .models import ActionItem, FollowUpItem


class ActionItemSerializer(serializers.ModelSerializer):
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = ActionItem
        fields = [
            "id",
            "user",
            "organization",
            "message",
            "source_approval",
            "title",
            "description",
            "owner",
            "owner_email",
            "due_date",
            "priority",
            "status",
            "confidence_score",
            "created_at",
            "updated_at",
        ]

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner else None


class FollowUpItemSerializer(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField()
    sender = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    open_url = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpItem
        fields = [
            "id",
            "user",
            "organization",
            "conversation",
            "last_message",
            "followup_due_at",
            "status",
            "created_at",
            "subject",
            "sender",
            "preview",
            "open_url",
        ]

    def get_subject(self, obj):
        if obj.last_message and obj.last_message.subject:
            return obj.last_message.subject
        if obj.conversation and obj.conversation.subject:
            return obj.conversation.subject
        return "No Subject"

    def get_sender(self, obj):
        if obj.last_message and obj.last_message.sender:
            return obj.last_message.sender
        return ""

    def get_preview(self, obj):
        if obj.last_message and obj.last_message.body:
            return obj.last_message.body[:140]
        return ""

    def get_open_url(self, obj):
        if obj.conversation_id:
            return f"/inbox?conversation={obj.conversation_id}"
        return "/inbox"