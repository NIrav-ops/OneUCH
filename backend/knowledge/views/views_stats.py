from django.db.models import Avg
from django.db.models import Sum

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
    KnowledgeJob,
)

from knowledge.serializers import (
    KnowledgeJobSerializer,
)


class KnowledgeStatisticsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        jobs = KnowledgeJob.objects.order_by(
            "-started_at"
        )[:10]

        stats = {

            "knowledge_evidence":

                KnowledgeEvidence.objects.count(),

            "knowledge_facts":

                KnowledgeFact.objects.count(),

            "jobs":

                KnowledgeJob.objects.count(),

            "processed_messages":

                KnowledgeJob.objects.aggregate(
                    total=Sum("processed")
                )["total"] or 0,

            "failed_messages":

                KnowledgeJob.objects.aggregate(
                    total=Sum("failed")
                )["total"] or 0,

            "average_duration":

                round(

                    KnowledgeJob.objects.aggregate(
                        avg=Avg("duration_seconds")
                    )["avg"] or 0,

                    2,

                ),

            "recent_jobs":

                KnowledgeJobSerializer(
                    jobs,
                    many=True,
                ).data,
        }

        return Response(stats)