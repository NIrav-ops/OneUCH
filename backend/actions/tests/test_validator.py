from django.test import TestCase
from django.contrib.auth import get_user_model

from inbox.models import Organization, InboxMessage
from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)
from actions.services.validator import ActionValidator
from actions.exceptions import InvalidAction

User = get_user_model()


class ActionValidatorTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
        )

        self.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.org,
            platform="gmail",
            direction="inbound",
            external_message_id="msg-001",
            sender="sender@test.com",
            recipients="user@test.com",
            subject="Subject",
            body="Body",
            received_at="2026-01-01T00:00:00Z",
        )

        self.workflow = WorkflowDefinition.objects.create(
            organization=self.org,
            name="Workflow",
            code="WF001",
            created_by=self.user,
        )

        self.instance = WorkflowInstance.objects.create(
            workflow=self.workflow,
            organization=self.org,
            started_by=self.user,
        )

    def test_email_action_validation(self):

        ActionValidator.validate_create({
            "user": self.user,
            "organization": self.org,
            "message": self.message,
            "title": "Email Action",
        })

    def test_workflow_action_validation(self):

        ActionValidator.validate_create({
            "organization": self.org,
            "workflow_instance": self.instance,
            "title": "Workflow Action",
            "source_type": "workflow",
        })

    def test_email_requires_message(self):

        with self.assertRaises(InvalidAction):

            ActionValidator.validate_create({
                "user": self.user,
                "organization": self.org,
                "title": "Email",
            })

    def test_workflow_requires_instance(self):

        with self.assertRaises(InvalidAction):

            ActionValidator.validate_create({
                "organization": self.org,
                "title": "Workflow",
                "source_type": "workflow",
            })