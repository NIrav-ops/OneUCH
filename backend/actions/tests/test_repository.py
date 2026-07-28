from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from inbox.models import Organization, InboxMessage
from actions.services.repository import ActionRepository

User = get_user_model()


class ActionRepositoryTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
        )

        self.org = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
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
            received_at=timezone.now(),
        )

    def test_create_action(self):

        action = ActionRepository.create_action(
            user=self.user,
            organization=self.org,
            message=self.message,
            title="Review Contract",
            priority=80,
        )

        self.assertEqual(action.title, "Review Contract")
        self.assertEqual(action.priority, 80)

    def test_complete_action(self):

        action = ActionRepository.create_action(
            user=self.user,
            organization=self.org,
            message=self.message,
            title="Complete Task",
        )

        ActionRepository.complete_action(action)

        action.refresh_from_db()

        self.assertEqual(action.status, "completed")
        self.assertIsNotNone(action.completed_at)

    def test_default_source_type(self):

        action = ActionRepository.create_action(
            user=self.user,
            organization=self.org,
            message=self.message,
            title="Review",
        )

        self.assertEqual(
            action.source_type,
            "email",
        )    