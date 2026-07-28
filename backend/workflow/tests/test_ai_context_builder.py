import json

from django.test import TestCase

from workflow.models import (
    WorkflowInstance,
)

from workflow.services.ai.context.builder import (
    AIContextBuilder,
)

from workflow.tests.utils import (
    create_workflow,
)


class DummyBusinessObject:
    """
    Minimal business-object-like object used to verify
    provider-independent context construction.
    """

    def __init__(
        self,
        object_id="Customer-001",
        object_type="customer",
        status="active",
    ):
        self.id = object_id
        self.object_type = object_type
        self.status = status


class AIContextBuilderTests(TestCase):

    def _create_instance(self):

        workflow = create_workflow()

        # Keep the historical test expectation deterministic.
        workflow.name = "AI Context Workflow"
        workflow.save(
            update_fields=[
                "name",
            ]
        )

        return WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

    def test_build_context(self):

        instance = self._create_instance()

        context = AIContextBuilder.build(
            workflow_instance=instance,
        )

        self.assertEqual(
            context["context_version"],
            "1.0",
        )

        self.assertEqual(
            context["workflow"][
                "workflow_name"
            ],
            "AI Context Workflow",
        )

        self.assertEqual(
            context["workflow"][
                "instance_id"
            ],
            str(instance.id),
        )

        self.assertEqual(
            context["workflow"][
                "workflow_id"
            ],
            str(instance.workflow_id),
        )

        self.assertEqual(
            context["workflow"]["status"],
            instance.status,
        )

        self.assertEqual(
            context["organization"]["id"],
            str(instance.organization_id),
        )

        self.assertEqual(
            context["actor"]["email"],
            instance.started_by.email,
        )

    def test_build_context_without_business_object(
        self,
    ):

        instance = self._create_instance()

        context = AIContextBuilder.build(
            workflow_instance=instance,
        )

        # Enterprise context uses a stable schema.
        # Optional sections remain present but are None.
        self.assertIn(
            "business_object",
            context,
        )

        self.assertIsNone(
            context["business_object"],
        )

    def test_build_context_with_business_object(
        self,
    ):

        instance = self._create_instance()

        business_object = (
            DummyBusinessObject()
        )

        context = AIContextBuilder.build(
            workflow_instance=instance,
            business_object=business_object,
        )

        self.assertIsNotNone(
            context["business_object"],
        )

        self.assertEqual(
            context["business_object"]["id"],
            "Customer-001",
        )

        self.assertEqual(
            context["business_object"]["type"],
            "customer",
        )

        self.assertEqual(
            context["business_object"]["status"],
            "active",
        )

    def test_runtime_context(self):

        instance = self._create_instance()

        context = AIContextBuilder.build(
            workflow_instance=instance,
            runtime_context={
                "priority": 80,
                "source": "workflow",
            },
        )

        self.assertEqual(
            context["runtime"]["priority"],
            80,
        )

        self.assertEqual(
            context["runtime"]["source"],
            "workflow",
        )

    def test_context_is_json_serializable(
        self,
    ):

        instance = self._create_instance()

        context = AIContextBuilder.build(
            workflow_instance=instance,
        )

        serialized = json.dumps(
            context
        )

        self.assertIsInstance(
            serialized,
            str,
        )