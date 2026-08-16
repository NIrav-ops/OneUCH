from rest_framework import serializers

from workflow.models import WorkflowDefinition


class WorkflowDefinitionSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = WorkflowDefinition

        fields = (
            "id",
            "name",
            "code",
            "description",
            "version",
            "status",
        )

        read_only_fields = (
            "id",
            "version",
            "status",
        )