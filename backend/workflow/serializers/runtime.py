from rest_framework import serializers

from workflow.models import WorkflowInstance


class WorkflowRuntimeSerializer(
    serializers.ModelSerializer
):

    workflow = serializers.UUIDField(
        source="workflow_id",
        read_only=True,
    )

    organization = serializers.UUIDField(
        source="organization_id",
        read_only=True,
    )

    class Meta:

        model = WorkflowInstance

        fields = [
            "id",
            "workflow",
            "organization",
            "status",
            "context",
            "started_at",
            "completed_at",
        ]

        read_only_fields = [
            "id",
            "workflow",
            "organization",
            "status",
            "context",
            "started_at",
            "completed_at",
        ]