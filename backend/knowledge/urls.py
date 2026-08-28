from django.urls import path

from knowledge.views.views_stats import (
    KnowledgeStatisticsAPIView,
)

from knowledge.views.views_attention import (
    AttentionAPIView,
)

urlpatterns = [

    path(
        "statistics/",
        KnowledgeStatisticsAPIView.as_view(),
        name="knowledge-statistics",
    ),

    path(
        "attention/",
        AttentionAPIView.as_view(),
        name="knowledge-attention",
    ),

]