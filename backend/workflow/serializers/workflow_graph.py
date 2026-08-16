from rest_framework import serializers


class WorkflowNodeSerializer(
    serializers.Serializer
):

    client_id = serializers.CharField()

    id = serializers.UUIDField(
        required=False,
        read_only=True,
    )

    name = serializers.CharField()

    node_type = serializers.CharField()

    configuration = serializers.JSONField(
        required=False,
        default=dict,
    )

    position_x = serializers.IntegerField(
        required=False,
        default=0,
    )

    position_y = serializers.IntegerField(
        required=False,
        default=0,
    )


class WorkflowTransitionSerializer(
    serializers.Serializer
):

    id = serializers.UUIDField(
        required=False,
        read_only=True,
    )

    source = serializers.CharField()

    target = serializers.CharField()

    priority = serializers.IntegerField(
        required=False,
        default=100,
    )

    condition = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class WorkflowGraphSerializer(
    serializers.Serializer
):

    workflow = serializers.UUIDField(
        required=True,
    )

    nodes = WorkflowNodeSerializer(
        many=True,
    )

    transitions = WorkflowTransitionSerializer(
        many=True,
    )


class WorkflowGraphResponseSerializer(
    serializers.Serializer
):
    """
    Canonical workflow designer state returned by the API.

    This is intentionally additive to the existing graph
    response contract. Existing frontend consumers can
    continue using `workflow`, `nodes` and `transitions`.
    """

    workflow = serializers.UUIDField()

    workflow_code = serializers.CharField()

    workflow_name = serializers.CharField()

    workflow_version = serializers.IntegerField()

    workflow_status = serializers.CharField()

    editable = serializers.BooleanField()

    nodes = WorkflowNodeSerializer(
        many=True,
    )

    transitions = WorkflowTransitionSerializer(
        many=True,
    )