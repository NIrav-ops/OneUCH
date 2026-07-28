from rest_framework import serializers


class CommunicationIntelligenceSerializer(
    serializers.Serializer,
):

    analytics = serializers.DictField()

    channels = serializers.DictField()

    trends = serializers.DictField()

    response_times = serializers.DictField()

    health = serializers.DictField()