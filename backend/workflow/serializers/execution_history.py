from rest_framework import serializers

from workflow.models import WorkflowExecutionLog


class WorkflowExecutionHistorySerializer(
    serializers.ModelSerializer
):

    node = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowExecutionLog

        fields = [
            "id",
            "event",
            "node",
            "details",
            "created_at",
        ]

        read_only_fields = fields

    def get_node(self, obj):

        if obj.node_id is None:
            return None

        return str(obj.node_id)