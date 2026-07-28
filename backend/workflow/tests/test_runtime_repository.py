from django.test import TestCase

from workflow.models import (
    WorkflowNode,
)

from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)

from workflow.tests.utils import create_workflow


class WorkflowRuntimeRepositoryTests(TestCase):

    def test_create_instance(self):

        workflow = create_workflow()

        instance = WorkflowRuntimeRepository.instance.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        self.assertEqual(
            instance.status,
            instance.STATUS_RUNNING,
        )

    def test_create_token(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        instance = WorkflowRuntimeRepository.instance.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        token = WorkflowRuntimeRepository.token.create(
            instance=instance,
            node=node,
        )

        self.assertEqual(
            token.node,
            node,
        )

    def test_create_log(self):

        workflow = create_workflow()

        instance = WorkflowRuntimeRepository.instance.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        log = WorkflowRuntimeRepository.log.create(
            instance=instance,
            event="Started",
        )

        self.assertEqual(
            log.event,
            "Started",
        )