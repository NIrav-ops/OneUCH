from rest_framework import serializers


class ExecutiveDashboardSerializer(serializers.Serializer):

    kpis = serializers.DictField()

    activity = serializers.ListField()

    alerts = serializers.DictField()

    risks = serializers.DictField()

    opportunities = serializers.DictField()

    communication = serializers.DictField()