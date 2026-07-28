from rest_framework import serializers


class SendEmailSerializer(serializers.Serializer):
    to_emails = serializers.ListField(
        child=serializers.EmailField()
    )
    subject = serializers.CharField()
    body = serializers.CharField()
    password = serializers.CharField(write_only=True)
