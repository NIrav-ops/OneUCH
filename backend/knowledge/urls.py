from django.urls import path

from knowledge.views.views_stats import (
    KnowledgeStatisticsAPIView,
)

urlpatterns = [

    path(
        "statistics/",
        KnowledgeStatisticsAPIView.as_view(),
        name="knowledge-statistics",
    ),

]