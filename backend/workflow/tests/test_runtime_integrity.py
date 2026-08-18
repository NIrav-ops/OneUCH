from django.test import TestCase
from django.utils import timezone

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
)

from workflow.services.runtime_integrity import (
    WorkflowRuntimeIntegrityError,
    WorkflowRuntimeIntegrityService,
)


class WorkflowRuntimeIntegrityTests(
    TestCase
):

    def setUp(self):

        from inbox.models import (
            Organization,
        )

        self.organization = (
            Organization.objects.create(
                name="Runtime Integrity Organization",
                slug="runtime-integrity-organization",
            )
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Integrity Workflow",
                code="INTEGRITY_WORKFLOW",
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

        self.start_node = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Start",
                node_type=WorkflowNode.START,
            )
        )

    def test_valid_instance_passes_integrity_check(
        self,
    ):

        self.assertTrue(
            WorkflowRuntimeIntegrityService
            .validate_instance(
                self.instance
            )
        )

    def test_valid_token_passes_integrity_check(
        self,
    ):

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=self.start_node,
            )
        )

        self.assertTrue(
            WorkflowRuntimeIntegrityService
            .validate_token(
                token
            )
        )

    def test_token_from_different_workflow_is_rejected(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Other Workflow",
                code="OTHER_INTEGRITY_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        other_node = (
            WorkflowNode.objects.create(
                workflow=other_workflow,
                name="Other Start",
                node_type=WorkflowNode.START,
            )
        )

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=other_node,
            )
        )

        with self.assertRaises(
            WorkflowRuntimeIntegrityError
        ):

            WorkflowRuntimeIntegrityService.validate_token(
                token
            )

    def test_terminal_instance_cannot_have_active_token(
        self,
    ):

        WorkflowToken.objects.create(
            instance=self.instance,
            node=self.start_node,
            status=WorkflowToken.STATUS_ACTIVE,
        )

        self.instance.status = (
            WorkflowInstance.STATUS_COMPLETED
        )

        self.instance.save(
            update_fields=[
                "status",
            ]
        )

        with self.assertRaises(
            WorkflowRuntimeIntegrityError
        ):

            WorkflowRuntimeIntegrityService.validate_instance(
                self.instance
            )

    def test_completed_token_requires_completion_timestamp(
        self,
    ):

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=self.start_node,
                status=(
                    WorkflowToken.STATUS_COMPLETED
                ),
            )
        )

        with self.assertRaises(
            WorkflowRuntimeIntegrityError
        ):

            WorkflowRuntimeIntegrityService.validate_token(
                token
            )

    def test_completed_token_with_timestamp_is_valid(
        self,
    ):

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=self.start_node,
                status=(
                    WorkflowToken.STATUS_COMPLETED
                ),
                completed_at=timezone.now(),
            )
        )

        self.assertTrue(
            WorkflowRuntimeIntegrityService
            .validate_token(
                token
            )
        )

    def test_waiting_token_requires_wait_state(
        self,
    ):

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=self.start_node,
                status=(
                    WorkflowToken.STATUS_WAITING
                ),
            )
        )

        with self.assertRaises(
            WorkflowRuntimeIntegrityError
        ):

            WorkflowRuntimeIntegrityService.validate_token(
                token
            )

    def test_waiting_token_with_reason_is_valid(
        self,
    ):

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=self.start_node,
                status=(
                    WorkflowToken.STATUS_WAITING
                ),
                wait_reason="approval",
            )
        )

        self.assertTrue(
            WorkflowRuntimeIntegrityService
            .validate_token(
                token
            )
        )