from rest_framework import serializers


class SearchSerializer(serializers.Serializer):

    business_objects = serializers.ListField()

    people = serializers.ListField()

    organizations = serializers.ListField()

    knowledge = serializers.ListField()