from unittest.mock import patch

from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)


class WorkflowRuntimeCancellationTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Cancellation Organization",
                slug="runtime-cancellation-organization",
            )
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Cancellation Workflow",
                code="CANCELLATION_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                context={},
            )
        )

        self.engine = WorkflowRuntimeEngine(
            self.instance
        )

    def test_cancel_running_workflow(
        self,
    ):

        with patch(
            "workflow.services.runtime_engine."
            "WorkflowExecutionEventService.record"
        ) as record_event:

            result = self.engine.cancel()

        self.instance.refresh_from_db()

        self.assertEqual(
            result.pk,
            self.instance.pk,
        )

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        self.assertIsNotNone(
            self.instance.completed_at
        )

        record_event.assert_called_once()

        call = (
            record_event.call_args
        )

        self.assertEqual(
            call.kwargs["instance"],
            self.instance,
        )

        self.assertEqual(
            call.kwargs["event"],
            (
                WorkflowExecutionEventService
                .WORKFLOW_CANCELLED
            ),
        )

    def test_cancel_does_not_change_workflow_version(
        self,
    ):

        original_workflow_id = (
            self.instance.workflow_id
        )

        original_version = (
            self.instance.workflow.version
        )

        self.engine.cancel()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.workflow_id,
            original_workflow_id,
        )

        self.assertEqual(
            self.instance.workflow.version,
            original_version,
        )

        self.assertEqual(
            self.instance.workflow.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

    def test_cancelled_workflow_cannot_run_again(
        self,
    ):

        self.engine.cancel()

        self.instance.refresh_from_db()

        with patch(
            "workflow.services.runtime_engine."
            "WorkflowExecutionEventService.record"
        ) as record_event:

            result = self.engine.run()

        self.assertEqual(
            result.pk,
            self.instance.pk,
        )

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        record_event.assert_not_called()

    def test_cancel_is_idempotent(
        self,
    ):

        self.engine.cancel()

        self.instance.refresh_from_db()

        first_completed_at = (
            self.instance.completed_at
        )

        with patch(
            "workflow.services.runtime_engine."
            "WorkflowExecutionEventService.record"
        ) as record_event:

            result = self.engine.cancel()

        self.instance.refresh_from_db()

        self.assertEqual(
            result.pk,
            self.instance.pk,
        )

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        self.assertEqual(
            self.instance.completed_at,
            first_completed_at,
        )

        record_event.assert_not_called()