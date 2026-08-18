from django.test import TestCase

from workflow.models import (
    WorkflowExecutionLog,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)

from workflow.tests.utils import (
    create_workflow,
)

from workflow.models import WorkflowInstance


class WorkflowExecutionHistoryIntegrityTests(
    TestCase
):

    def setUp(self):

        self.workflow = create_workflow()

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.workflow.organization,
            )
        )

    def test_execution_history_can_be_created(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        self.assertIsNotNone(
            event.pk
        )

        self.assertEqual(
            WorkflowExecutionLog.objects.count(),
            1,
        )

    def test_execution_history_update_is_rejected(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        with self.assertRaises(
            PermissionError
        ):

            WorkflowRuntimeRepository.log.update(
                event,
                event="tampered",
            )

    def test_execution_history_delete_is_rejected(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        with self.assertRaises(
            PermissionError
        ):

            WorkflowRuntimeRepository.log.delete(
                event
            )

        self.assertTrue(
            WorkflowExecutionLog.objects.filter(
                pk=event.pk
            ).exists()
        )

    def test_history_is_ordered_as_execution_timeline(
        self,
    ):

        first = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        second = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_COMPLETED
                ),
            )
        )

        history = list(
            WorkflowRuntimeRepository
            .log
            .for_instance(
                self.instance
            )
        )

        self.assertEqual(
            [event.pk for event in history],
            [
                first.pk,
                second.pk,
            ],
        )

    def test_history_is_scoped_to_execution_instance(
        self,
    ):

        other_instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.workflow.organization,
            )
        )

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        WorkflowExecutionEventService.record(
            instance=other_instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        history = list(
            WorkflowRuntimeRepository
            .log
            .for_instance(
                self.instance
            )
        )

        self.assertEqual(
            len(history),
            1,
        )

        self.assertEqual(
            history[0].instance_id,
            self.instance.pk,
        )

    def test_history_service_returns_read_only_query_boundary(
        self,
    ):

        from workflow.services.execution.execution_history import (
            WorkflowExecutionHistoryService,
        )

        history = (
            WorkflowExecutionHistoryService
            .get_for_instance(
                self.instance
            )
        )

        self.assertEqual(
            history.count(),
            0,
        )

        self.assertTrue(
            WorkflowExecutionHistoryService
            .assert_read_only()
        )