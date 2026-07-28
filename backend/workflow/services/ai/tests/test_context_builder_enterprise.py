import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from workflow.services.ai.context.builder import (
    AIContextBuilder,
)


class DummyOrganization:

    def __init__(self):

        self.id = 10
        self.name = "One UCH Test"
        self.slug = "one-uch-test"


class DummyUser:

    def __init__(self):

        self.id = 20
        self.email = "admin@test.com"
        self.role = "admin"


class DummyWorkflow:

    def __init__(self):

        self.id = uuid4()
        self.name = "Finance Workflow"


class DummyWorkflowInstance:

    def __init__(self):

        self.id = uuid4()

        self.workflow = (
            DummyWorkflow()
        )

        self.workflow_id = (
            self.workflow.id
        )

        self.organization = (
            DummyOrganization()
        )

        self.started_by = (
            DummyUser()
        )

        self.status = "running"


class DummyBusinessObjectType:

    def __init__(self):

        self.name = "Purchase Order"


class DummyBusinessObject:

    def __init__(self):

        self.id = 100

        self.object_type = (
            DummyBusinessObjectType()
        )

        self.status = "open"


class EnterpriseAIContextBuilderTests(
    SimpleTestCase
):

    def test_build_workflow_context(self):

        instance = (
            DummyWorkflowInstance()
        )

        result = AIContextBuilder.build(
            workflow_instance=instance,
        )

        self.assertEqual(
            result["workflow"][
                "workflow_name"
            ],
            "Finance Workflow",
        )

        self.assertEqual(
            result["workflow"]["status"],
            "running",
        )

        self.assertEqual(
            result["context_version"],
            "1.0",
        )

    def test_build_organization_context(
        self,
    ):

        result = AIContextBuilder.build(
            workflow_instance=(
                DummyWorkflowInstance()
            )
        )

        organization = result[
            "organization"
        ]

        self.assertEqual(
            organization["name"],
            "One UCH Test",
        )

        self.assertEqual(
            organization["slug"],
            "one-uch-test",
        )

    def test_build_actor_context(self):

        result = AIContextBuilder.build(
            workflow_instance=(
                DummyWorkflowInstance()
            )
        )

        actor = result["actor"]

        self.assertEqual(
            actor["email"],
            "admin@test.com",
        )

        self.assertEqual(
            actor["role"],
            "admin",
        )

    def test_build_business_object_context(
        self,
    ):

        result = AIContextBuilder.build(
            business_object=(
                DummyBusinessObject()
            )
        )

        business_object = result[
            "business_object"
        ]

        self.assertEqual(
            business_object["id"],
            "100",
        )

        self.assertEqual(
            business_object["type"],
            "Purchase Order",
        )

        self.assertEqual(
            business_object["status"],
            "open",
        )

    def test_dictionary_business_object_supported(
        self,
    ):

        result = AIContextBuilder.build(
            business_object={
                "id": uuid4(),
                "type": "invoice",
            }
        )

        # Final context must still be JSON safe.
        json.dumps(result)

        self.assertEqual(
            result["business_object"][
                "type"
            ],
            "invoice",
        )

    def test_runtime_context_preserved(self):

        result = AIContextBuilder.build(
            runtime_context={
                "priority": 80,
                "source": "workflow",
            }
        )

        self.assertEqual(
            result["runtime"]["priority"],
            80,
        )

        self.assertEqual(
            result["runtime"]["source"],
            "workflow",
        )

    def test_context_is_json_serializable(
        self,
    ):

        result = AIContextBuilder.build(
            workflow_instance=(
                DummyWorkflowInstance()
            ),
            business_object={
                "id": uuid4(),
                "created_at": datetime.now(),
                "amount": Decimal(
                    "1250.50"
                ),
            },
            runtime_context={
                "request_id": uuid4(),
            },
        )

        serialized = json.dumps(
            result
        )

        self.assertIsInstance(
            serialized,
            str,
        )

    def test_empty_context_supported(self):

        result = (
            AIContextBuilder.build()
        )

        self.assertEqual(
            result["context_version"],
            "1.0",
        )

        self.assertIsNone(
            result["workflow"]
        )

        self.assertIsNone(
            result["organization"]
        )

        self.assertIsNone(
            result["actor"]
        )

        self.assertIsNone(
            result["business_object"]
        )

        self.assertEqual(
            result["runtime"],
            {},
        )