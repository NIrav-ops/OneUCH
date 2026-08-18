from django.test import TestCase

from workflow.models import (
    WorkflowExecutionLog,
    WorkflowInstance,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.services.execution_integrity import (
    WorkflowExecutionEventIntegrityError,
    WorkflowExecutionEventIntegrityService,
)

from workflow.services.execution.history_integrity import (
    WorkflowExecutionHistoryIntegrityService,
)

from workflow.tests.utils import (
    create_workflow,
)


class WorkflowExecutionEventIntegrityTests(
    TestCase
):

    def setUp(self):

        self.workflow = create_workflow()

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=(
                    self.workflow.organization
                ),
            )
        )

    def test_first_event_has_sequence_one(
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

        self.assertEqual(
            event.sequence_number,
            1,
        )

        self.assertIsNone(
            event.previous_event_hash
        )

        self.assertIsNotNone(
            event.event_hash
        )

        self.assertEqual(
            len(event.event_hash),
            64,
        )

    def test_second_event_links_to_first_event(
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

        self.assertEqual(
            second.sequence_number,
            2,
        )

        self.assertEqual(
            second.previous_event_hash,
            first.event_hash,
        )

        self.assertNotEqual(
            second.event_hash,
            first.event_hash,
        )

    def test_event_hash_is_valid(
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

        self.assertTrue(
            WorkflowExecutionEventIntegrityService
            .verify_event(event)
        )

    def test_complete_history_is_valid(
        self,
    ):

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .NODE_STARTED
            ),
        )

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .NODE_COMPLETED
            ),
        )

        result = (
            WorkflowExecutionHistoryIntegrityService
            .verify_instance(
                self.instance
            )
        )

        self.assertTrue(
            result["valid"]
        )

        self.assertEqual(
            result["event_count"],
            3,
        )

        self.assertIsNotNone(
            result["last_event_hash"]
        )

    def test_tampered_details_are_detected(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                details={
                    "business_action": "approved",
                },
            )
        )

        WorkflowExecutionLog.objects.filter(
            pk=event.pk
        ).update(
            details={
                "business_action": "rejected",
            }
        )

        event.refresh_from_db()

        with self.assertRaises(
            WorkflowExecutionEventIntegrityError
        ):

            WorkflowExecutionEventIntegrityService.verify_event(
                event
            )

    def test_tampered_event_hash_is_detected(
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

        WorkflowExecutionLog.objects.filter(
            pk=event.pk
        ).update(
            event_hash="0" * 64
        )

        event.refresh_from_db()

        with self.assertRaises(
            WorkflowExecutionEventIntegrityError
        ):

            WorkflowExecutionEventIntegrityService.verify_event(
                event
            )

    def test_tampered_chain_is_detected(
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

        WorkflowExecutionLog.objects.filter(
            pk=second.pk
        ).update(
            previous_event_hash="0" * 64
        )

        second.refresh_from_db()

        with self.assertRaises(
            WorkflowExecutionEventIntegrityError
        ):

            WorkflowExecutionHistoryIntegrityService.verify_instance(
                self.instance
            )

        self.assertIsNotNone(
            first.event_hash
        )

    def test_caller_cannot_supply_integrity_fields(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                details={
                    "event_hash": (
                        "attacker-controlled"
                    ),
                    "previous_event_hash": (
                        "attacker-controlled"
                    ),
                    "sequence_number": 999,
                },
            )
        )

        self.assertEqual(
            event.sequence_number,
            1,
        )

        self.assertNotEqual(
            event.event_hash,
            "attacker-controlled",
        )

        self.assertIsNone(
            event.previous_event_hash
        )