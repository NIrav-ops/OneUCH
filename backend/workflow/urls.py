from django.urls import path

from workflow.views_graph import (
    WorkflowGraphAPIView,
)

from workflow.views_definition import (
    WorkflowDefinitionAPIView,
)

from workflow.views_publish import (
    WorkflowPublishAPIView,
)

from workflow.views_runtime import (
    WorkflowRuntimeAPIView,
    WorkflowRuntimeCreateAPIView,
)

from workflow.views_execution_history import (
    WorkflowExecutionHistoryAPIView,
)

urlpatterns = [

    path(
        "builder/graph/",
        WorkflowGraphAPIView.as_view(),
        name="workflow-builder-graph",
    ),

    path(
        "definitions/",
        WorkflowDefinitionAPIView.as_view(),
        name="workflow-definitions",
    ),

    path(
        "definitions/<uuid:pk>/",
        WorkflowDefinitionAPIView.as_view(),
        name="workflow-definition-detail",
    ),

    path(
        "definitions/<uuid:workflow_id>/publish/",
        WorkflowPublishAPIView.as_view(),
        name="workflow-publish",
    ),

    path(
        "definitions/<uuid:workflow_id>/runtime/",
        WorkflowRuntimeCreateAPIView.as_view(),
        name="workflow-runtime-create",
    ),

    path(
        "runtime/<uuid:instance_id>/",
        WorkflowRuntimeAPIView.as_view(),
        name="workflow-runtime",
    ),

    path(
        "runtime/<uuid:instance_id>/history/",
        WorkflowExecutionHistoryAPIView.as_view(),
        name="workflow-runtime-history",
    ),
]