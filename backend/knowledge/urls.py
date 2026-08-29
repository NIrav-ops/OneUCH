from django.urls import path

from knowledge.views.views_stats import (
    KnowledgeStatisticsAPIView,
)

from knowledge.views.views_attention import (
    AttentionAPIView,
)

from knowledge.views.views_commitments import (
    CommitmentsAPIView,
)

from knowledge.views.views_waiting_for import (
    WaitingForAPIView,
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

    path(
        "commitments/",
        CommitmentsAPIView.as_view(),
        name="knowledge-commitments",
    ),

    path(
        "waiting-for/",
        WaitingForAPIView.as_view(),
        name="knowledge-waiting-for",
    ),



]