from rest_framework import serializers

from knowledge.models import KnowledgeJob


class KnowledgeJobSerializer(serializers.ModelSerializer):

    class Meta:

        model = KnowledgeJob

        fields = [
            "id",
            "job_type",
            "status",
            "processed",
            "skipped",
            "failed",
            "duration_seconds",
            "started_at",
            "completed_at",
        ]