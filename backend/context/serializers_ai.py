from rest_framework import serializers


class AIIntelligenceSerializer(serializers.Serializer):

    briefing = serializers.DictField()

    recommendations = serializers.ListField()

    risk = serializers.DictField()

    opportunity = serializers.DictField()