from django.shortcuts import get_object_or_404

from platform_core.api.tenant import (
    get_user_organization_or_404,
)

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import WorkflowDefinition

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowPublishAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    service = WorkflowBuilderService()

    def post(
        self,
        request,
        workflow_id,
    ):

        #
        # Tenant identity is derived exclusively from
        # the authenticated user's membership.
        #

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        #
        # Resolve the workflow inside that tenant.
        #
        # Cross-tenant IDs intentionally return 404
        # so resource existence is not disclosed.
        #

        workflow = get_object_or_404(
            WorkflowDefinition,
            pk=workflow_id,
            organization=organization,
        )

        #
        # Execute workflow lifecycle validation.
        #

        try:

            workflow = self.service.publish(
                workflow
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        #
        # Successful publication.
        #

        return Response(
            {
                "status": "success",

                "workflow": {
                    "id": str(
                        workflow.pk
                    ),

                    "name": workflow.name,

                    "code": workflow.code,

                    "version": workflow.version,

                    "status": workflow.status,
                }
            },
            status=status.HTTP_200_OK,
        )