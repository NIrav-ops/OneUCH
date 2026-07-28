from rest_framework import serializers


class HealthSerializer(serializers.Serializer):

    service = serializers.CharField()

    status = serializers.CharField()

    details = serializers.DictField()


class MetricsSerializer(serializers.Serializer):

    services = serializers.IntegerField()

    queued_jobs = serializers.IntegerField()

    completed_jobs = serializers.IntegerField()

    notifications = serializers.IntegerField()

    audit_events = serializers.IntegerField()


class ConfigurationSerializer(serializers.Serializer):

    key = serializers.CharField()

    value = serializers.JSONField()