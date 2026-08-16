from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import WorkflowInstance

from workflow.serializers.runtime import (
    WorkflowRuntimeSerializer,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)

from workflow.services.runtime_governance import (
    WorkflowRuntimeGovernance,
    WorkflowRuntimeGovernanceError,
)


class WorkflowRuntimeAPIView(
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

    def _get_instance(
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

            return None

        return get_object_or_404(
            WorkflowInstance,
            pk=instance_id,
            organization=organization,
        )

    def get(
        self,
        request,
        instance_id,
    ):

        instance = self._get_instance(
            request,
            instance_id,
        )

        if instance is None:

            return Response(
                {
                    "detail": (
                        "Authenticated user is not "
                        "associated with an organization."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

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

        serializer = WorkflowRuntimeSerializer(
            instance
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(
        self,
        request,
        instance_id,
    ):

        instance = self._get_instance(
            request,
            instance_id,
        )

        if instance is None:

            return Response(
                {
                    "detail": (
                        "Authenticated user is not "
                        "associated with an organization."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        action = (
            request.data.get(
                "action"
            )
        )

        if action not in {
            "run",
            "resume",
            "cancel",
        }:

            return Response(
                {
                    "detail": (
                        "Unsupported runtime action."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        #
        # Runtime governance is evaluated before
        # the execution engine is invoked.
        #
        # This prevents unauthorized users from
        # reaching run/resume/cancel operations.
        #

        try:

            WorkflowRuntimeGovernance.authorize(
                user=request.user,
                instance=instance,
                action=action,
            )

        except WorkflowRuntimeGovernanceError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        engine = WorkflowRuntimeEngine(
            instance,
            actor=request.user,
            actor_type="user",
            source="runtime_api",
        )

        try:

            if action == "run":

                result = engine.run()

            elif action == "resume":

                result = engine.resume()

            else:

                result = engine.cancel()

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = WorkflowRuntimeSerializer(
            result
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )