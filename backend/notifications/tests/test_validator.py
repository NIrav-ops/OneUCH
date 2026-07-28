from django.test import TestCase

from notifications.exceptions import InvalidNotification
from notifications.services.validator import NotificationValidator


class NotificationValidatorTests(TestCase):

    def test_missing_title(self):

        with self.assertRaises(InvalidNotification):

            NotificationValidator.validate_create({
                "organization": object(),
                "message": "Hello",
                "type": "system",
            })

    def test_invalid_channel(self):

        with self.assertRaises(InvalidNotification):

            NotificationValidator.validate_create({
                "organization": object(),
                "title": "Hello",
                "message": "World",
                "type": "system",
                "channel": "discord",
            })

    def test_invalid_type(self):

        with self.assertRaises(InvalidNotification):

            NotificationValidator.validate_create({
                "organization": object(),
                "title": "Hello",
                "message": "World",
                "type": "abc",
            })