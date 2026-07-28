from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from inbox.models import (
    Organization,
    OrganizationUser,
)

from platform_core.context.organization import (
    OrganizationResolver,
)


User = get_user_model()


class OrganizationContextTests(TestCase):

    def test_anonymous(self):

        factory = RequestFactory()

        request = factory.get("/")

        request.user = None

        self.assertIsNone(

            OrganizationResolver.resolve(
                request,
            )

        )

    def test_authenticated_without_org(self):

        factory = RequestFactory()

        request = factory.get("/")

        user = User.objects.create_user(
            email="john@example.com",
            password="pass123",
        )

        request.user = user

        self.assertIsNone(

            OrganizationResolver.resolve(
                request,
            )

        )

    def test_membership_resolution(self):

        factory = RequestFactory()

        request = factory.get("/")

        user = User.objects.create_user(
            email="alice@example.com",
            password="pass123",
    )

        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )

        OrganizationUser.objects.create(
            user=user,
            organization=org,
        )

        request.user = user

        self.assertEqual(
            OrganizationResolver.resolve(request),
            org,
        )