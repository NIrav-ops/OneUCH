from django.urls import path

from context.views_customer360 import (
    Customer360APIView,
)

from context.views_organization360 import (
    Organization360APIView,
)

from context.views_people360 import (
    People360APIView,
)

from context.views_communication import (
    CommunicationIntelligenceAPIView,
)

from context.views_executive_dashboard import (
    ExecutiveDashboardAPIView,
)

from context.views_search import SearchAPIView

from context.views_ai import (
    AIIntelligenceAPIView,
)

from context.views_risk import (
    ExecutiveRiskAPIView,
)

from context.views_opportunity import (
    ExecutiveOpportunityAPIView,
)

from context.views_workflow import (
    WorkflowIntelligenceAPIView,
)

urlpatterns = [

    path(
        "customer360/<int:business_object_id>/",
        Customer360APIView.as_view(),
        name="customer360",
    ),

    path(
        "organization360/<int:organization_id>/",
        Organization360APIView.as_view(),
        name="organization360",
    ),

    path(
        "people360/<int:person_id>/",
        People360APIView.as_view(),
        name="people360",
    ),

    path(
        "communication/<int:organization_id>/",
        CommunicationIntelligenceAPIView.as_view(),
        name="communication-intelligence",
    ),

    path(
        "executive-dashboard/<int:organization_id>/",
        ExecutiveDashboardAPIView.as_view(),
        name="executive-dashboard",
    ),

    path(
        "search/<int:organization_id>/",
        SearchAPIView.as_view(),
        name="enterprise-search",
    ),

    path(
        "ai/<int:organization_id>/",
        AIIntelligenceAPIView.as_view(),
        name="ai-intelligence",
    ),

    path(
        "risk/<int:organization_id>/",
        ExecutiveRiskAPIView.as_view(),
        name="executive-risk",
    ),
    
    path(
        "opportunity/<int:organization_id>/",
        ExecutiveOpportunityAPIView.as_view(),
        name="executive-opportunity",
    ),

    path(
        "workflow/<int:organization_id>/",
        WorkflowIntelligenceAPIView.as_view(),
        name="workflow-intelligence",
    ),
]