from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404

from workflow.models import WorkflowDefinition

from workflow.serializers.workflow_definition import (
    WorkflowDefinitionSerializer,
)

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowDefinitionAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    service = WorkflowBuilderService()

    def _get_organization(
        self,
        user,
    ):

        organization = getattr(
            user,
            "organization",
            None,
        )

        if organization is None:

            raise ValueError(
                "Authenticated user is not associated with an organization."
            )

        return organization

    def get_workflow(
        self,
        request,
        pk,
    ):

        organization = self._get_organization(
            request.user
        )

        workflow = get_object_or_404(
            WorkflowDefinition,
            pk=pk,
            organization=organization,
        )

        return workflow

    def get(
        self,
        request,
        pk=None,
    ):

        organization = self._get_organization(
            request.user
        )

        if pk is not None:

            workflow = self.get_workflow(
                request,
                pk,
            )

            return Response(
                WorkflowDefinitionSerializer(
                    workflow
                ).data
            )

        workflows = (
            self.service.list_workflows(
                organization
            )
        )

        return Response(
            WorkflowDefinitionSerializer(
                workflows,
                many=True,
            ).data
        )

    def post(
        self,
        request,
    ):

        organization = self._get_organization(
            request.user
        )

        serializer = WorkflowDefinitionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        workflow = (
            self.service.create_workflow(

                organization=organization,

                created_by=request.user,

                **serializer.validated_data,
            )
        )

        return Response(

            WorkflowDefinitionSerializer(
                workflow
            ).data,

            status=status.HTTP_201_CREATED,
        )

    def put(
        self,
        request,
        pk,
    ):

        workflow = self.get_workflow(
            request,
            pk,
        )

        serializer = WorkflowDefinitionSerializer(
            workflow,
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True
        )

        workflow = (
            self.service.update_workflow(

                workflow,

                name=serializer.validated_data.get(
                    "name"
                ),

                code=serializer.validated_data.get(
                    "code"
                ),

                description=serializer.validated_data.get(
                    "description"
                ),
            )
        )

        return Response(
            WorkflowDefinitionSerializer(
                workflow
            ).data
        )

    def delete(
        self,
        request,
        pk,
    ):

        workflow = self.get_workflow(
            request,
            pk,
        )

        #
        # Active workflows should not be
        # silently deleted.
        #

        if workflow.status == (
            WorkflowDefinition.STATUS_ACTIVE
        ):

            return Response(
                {
                    "detail": (
                        "Active workflows cannot "
                        "be deleted."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        self.service.delete_workflow(
            workflow
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )