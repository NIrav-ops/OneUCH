from rest_framework import serializers


class WorkflowIntelligenceSerializer(serializers.Serializer):

    dashboard = serializers.DictField()