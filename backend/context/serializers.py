from rest_framework import serializers


class Customer360Serializer(serializers.Serializer):

    business_object = serializers.DictField()

    graph = serializers.DictField()

    relationships = serializers.DictField()

    knowledge = serializers.DictField()

    timeline = serializers.ListField()

    activity = serializers.ListField()

    metrics = serializers.DictField()

    summary = serializers.DictField()

    health = serializers.DictField()