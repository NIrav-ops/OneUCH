from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import WorkflowDefinition

from workflow.serializers.workflow_graph import (
    WorkflowGraphSerializer,
)

from workflow.services.builder.graph_service import (
    WorkflowGraphService,
)


class WorkflowGraphAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    service = WorkflowGraphService()

    def _get_organization(
        self,
        request,
    ):

        membership = getattr(
            request.user,
            "organization_membership",
            None,
        )

        if membership is None:
            return None

        return membership.organization

    def get(
        self,
        request,
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

        workflow_id = request.query_params.get(
            "workflow"
        )

        if not workflow_id:

            return Response(
                {
                    "detail": (
                        "workflow query parameter is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow = get_object_or_404(
            WorkflowDefinition,
            pk=workflow_id,
            organization=organization,
        )

        result = self.service.get_graph(
            workflow=workflow,
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    def post(
        self,
        request,
    ):

        serializer = WorkflowGraphSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        workflow_id = (
            serializer.validated_data[
                "workflow"
            ]
        )

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

        workflow = get_object_or_404(
            WorkflowDefinition,
            pk=workflow_id,
            organization=organization,
        )

        try:

            result = self.service.save_graph(

                workflow=workflow,

                graph=serializer.validated_data,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "status": "success",

                "workflow": result[
                    "workflow_id"
                ],

                "nodes": result[
                    "nodes"
                ],
            },
            status=status.HTTP_200_OK,
        )