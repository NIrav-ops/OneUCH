from rest_framework import serializers


class ExecutiveRiskSerializer(serializers.Serializer):

    communication = serializers.DictField()

    knowledge = serializers.DictField()

    relationship = serializers.DictField()

    organization = serializers.DictField()