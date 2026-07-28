from django.test import TestCase

from workflow.services.repository import WorkflowRepository

from workflow.tests.utils import create_workflow


class WorkflowRepositoryTests(TestCase):

    def test_get_workflow(self):

        workflow = create_workflow()

        result = WorkflowRepository.definition.get(
            workflow.id
        )

        self.assertEqual(
            result.id,
            workflow.id,
        )

    def test_list_workflows(self):

        workflow = create_workflow()

        workflows = WorkflowRepository.definition.list(
            workflow.organization,
        )

        self.assertEqual(
            workflows.count(),
            1,
        )

    def test_active_workflows(self):

        workflow = create_workflow()

        workflow.status = workflow.STATUS_ACTIVE
        workflow.save()

        active = WorkflowRepository.definition.active(
            workflow.organization,
        )

        self.assertEqual(
            active.count(),
            1,
        )