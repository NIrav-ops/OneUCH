from django.db import transaction

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)


class WorkflowRuntimeInstanceService:
    """
    Creates WorkflowInstance records from published workflow
    definitions.

    This service is intentionally separate from
    WorkflowRuntimeEngine.

    Instance creation establishes the runtime identity.
    WorkflowRuntimeEngine is responsible for execution.
    """

    @staticmethod
    @transaction.atomic
    def create_instance(
        *,
        workflow,
        organization,
        started_by=None,
        context=None,
    ):
        """
        Create one runtime instance pinned to the supplied
        WorkflowDefinition.

        The WorkflowInstance.workflow foreign key preserves
        the exact workflow definition/version used by the
        execution.
        """

        if workflow.organization_id != organization.pk:
            raise ValueError(
                "Workflow does not belong to the requested organization."
            )

        if workflow.status != (
            WorkflowDefinition.STATUS_ACTIVE
        ):
            raise ValueError(
                "Only active workflows can be executed."
            )

        runtime_context = (
            dict(context)
            if context is not None
            else {}
        )

        return WorkflowInstance.objects.create(
            workflow=workflow,
            organization=organization,
            started_by=started_by,
            context=runtime_context,
            status=WorkflowInstance.STATUS_RUNNING,
        )