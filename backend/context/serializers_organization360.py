from rest_framework import serializers


class Organization360Serializer(serializers.Serializer):
    organization = serializers.DictField()

    metrics = serializers.DictField()

    activity = serializers.ListField()

    health = serializers.DictField()