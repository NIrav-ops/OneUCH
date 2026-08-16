from django.test import TestCase

from workflow.models import (
    WorkflowDefinition,
)

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowDefinitionServiceTests(
    TestCase
):

    def setUp(self):

        self.organization = None

        self.service = WorkflowBuilderService()

    def test_service_class_exists(self):

        self.assertIsNotNone(
            self.service
        )

    def test_repository_methods_exist(self):

        self.assertTrue(
            hasattr(
                self.service,
                "create_workflow",
            )
        )

        self.assertTrue(
            hasattr(
                self.service,
                "list_workflows",
            )
        )

        self.assertTrue(
            hasattr(
                self.service,
                "get_workflow",
            )
        )

        self.assertTrue(
            hasattr(
                self.service,
                "update_workflow",
            )
        )

        self.assertTrue(
            hasattr(
                self.service,
                "delete_workflow",
            )
        )