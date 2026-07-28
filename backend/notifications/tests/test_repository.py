from django.test import TestCase
from django.contrib.auth import get_user_model

from inbox.models import Organization
from notifications.models import Notification
from notifications.services.repository import NotificationRepository

User = get_user_model()


class NotificationRepositoryTests(TestCase):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Cyberllix"
        )

        self.user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
        )

    def test_create_notification(self):

        notification = NotificationRepository.create_notification(
            organization=self.organization,
            user=self.user,
            title="Test",
            message="Hello",
            type="system",
        )

        self.assertEqual(
            notification.status,
            "pending",
        )

        self.assertEqual(
            notification.channel,
            "in_app",
        )

    def test_mark_read(self):

        notification = NotificationRepository.create_notification(
            organization=self.organization,
            user=self.user,
            title="Test",
            message="Hello",
            type="system",
        )

        NotificationRepository.mark_read(notification)

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)

    def test_mark_sent(self):

        notification = NotificationRepository.create_notification(
            organization=self.organization,
            user=self.user,
            title="Test",
            message="Hello",
            type="system",
        )

        NotificationRepository.mark_sent(notification)

        notification.refresh_from_db()

        self.assertEqual(
            notification.status,
            "sent",
        )