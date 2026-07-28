from rest_framework import serializers


class People360Serializer(serializers.Serializer):

    person = serializers.DictField()

    timeline = serializers.ListField()

    metrics = serializers.DictField()

    health = serializers.DictField()