from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from knowledge.models import (
    BusinessIdentity,
)

from knowledge.services.resolver import (
    BusinessObjectResolver,
)


class BusinessObjectResolverTests(TestCase):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Test Organization",
        )

        self.object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        self.google = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        BusinessIdentity.objects.create(
            business_object=self.google,
            identity_type="EMAIL",
            value="support@google.com",
            normalized_value="support@google.com",
            source="manual",
        )

    def test_email_identity_match(self):

        result = BusinessObjectResolver.resolve(
            organization=self.organization,
            sender="support@google.com",
            subject="Test",
            body="",
        )

        self.assertTrue(result["matched"])

        self.assertEqual(
            result["best_match"]["business_object"].id,
            self.google.id,
        )

    def test_unknown_sender(self):

        result = BusinessObjectResolver.resolve(
            organization=self.organization,
            sender="abc@xyz.com",
            subject="Hello",
            body="",
        )

        self.assertFalse(result["matched"])

    def test_case_insensitive_email(self):

        result = BusinessObjectResolver.resolve(
            organization=self.organization,
            sender="Support@Google.com",
            subject="Hello",
            body="",
        )

        self.assertTrue(result["matched"])

    def test_empty_message(self):

        result = BusinessObjectResolver.resolve(
            organization=self.organization,
            sender="",
            subject="",
            body="",
        )

        self.assertFalse(result["matched"])