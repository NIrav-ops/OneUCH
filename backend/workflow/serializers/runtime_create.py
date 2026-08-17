from rest_framework import serializers


class WorkflowRuntimeCreateSerializer(
    serializers.Serializer
):

    context = serializers.JSONField(
        required=False,
        default=dict,
    )

    def validate_context(self, value):

        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Workflow context must be a JSON object."
            )

        return value