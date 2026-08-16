from django.shortcuts import get_object_or_404

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
        # First resolve the workflow itself.
        #
        # This guarantees that a genuinely missing
        # workflow returns HTTP 404 before any
        # organization authorization logic is evaluated.
        #

        workflow = get_object_or_404(
            WorkflowDefinition,
            pk=workflow_id,
        )

        #
        # Resolve the authenticated user's organization.
        #

        organization = getattr(
            request.user,
            "organization",
            None,
        )

        #
        # The current User model does not expose an
        # organization field directly.
        #
        # Therefore an authenticated user without an
        # organization cannot publish a workflow.
        #

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

        #
        # Enforce tenant isolation.
        #
        # A workflow belonging to another organization
        # cannot be published by this user.
        #

        if workflow.organization_id != organization.id:

            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to publish this workflow."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
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