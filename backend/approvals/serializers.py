from rest_framework import serializers
from .models import ApprovalItem


class ApprovalItemSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalItem
        fields = [
            "id",
            "user",
            "organization",
            "message",
            "conversation",
            "title",
            "description",
            "requested_by",
            "assigned_to",
            "assigned_to_email",
            "status",
            "due_date",
            "confidence_score",
            "decision_notes",
            "approval_analyzed",
            "created_at",
            "updated_at",
        ]

    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None