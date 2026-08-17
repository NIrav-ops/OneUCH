from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import WorkflowInstance

from workflow.serializers.execution_history import (
    WorkflowExecutionHistorySerializer,
)

from workflow.services.runtime_governance import (
    WorkflowRuntimeGovernance,
    WorkflowRuntimeGovernanceError,
)

from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)


class WorkflowExecutionHistoryAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def _get_organization(
        self,
        request,
    ):

        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if organization is not None:
            return organization

        membership = getattr(
            request.user,
            "organization_membership",
            None,
        )

        if membership is not None:
            return membership.organization

        return None

    def get(
        self,
        request,
        instance_id,
    ):

        organization = (
            self._get_organization(
                request
            )
        )

        if organization is None:

            return Response(
                {
                    "detail": (
                        "Authenticated user is not "
                        "associated with an organization."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = get_object_or_404(
            WorkflowInstance,
            pk=instance_id,
            organization=organization,
        )

        #
        # Execution history is an audit surface.
        #
        # Organization scoping alone is not sufficient.
        # Apply the same runtime governance boundary used
        # by the runtime inspection API.
        #

        try:

            WorkflowRuntimeGovernance.authorize(
                user=request.user,
                instance=instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_VIEW
                ),
            )

        except WorkflowRuntimeGovernanceError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        logs = (
            WorkflowRuntimeRepository
            .log
            .for_instance(instance)
        )

        serializer = (
            WorkflowExecutionHistorySerializer(
                logs,
                many=True,
            )
        )

        return Response(
            {
                "instance": str(
                    instance.pk
                ),
                "workflow": str(
                    instance.workflow_id
                ),
                "workflow_version": (
                    instance.workflow.version
                ),
                "events": serializer.data,
            },
            status=status.HTTP_200_OK,
        )