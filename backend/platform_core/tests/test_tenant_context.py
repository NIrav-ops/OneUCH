from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from inbox.models import Organization, OrganizationUser

from platform_core.context.tenant import TenantResolver

User = get_user_model()


class TenantResolverTests(TestCase):

    def test_anonymous(self):

        request = RequestFactory().get("/")

        request.user = None

        self.assertIsNone(
            TenantResolver.resolve(request)
        )

    def test_tenant_created(self):

        user = User.objects.create_user(
            email="tenant@example.com",
            password="pass123",
        )

        organization = Organization.objects.create(
            name="Tenant Org",
            slug="tenant-org",
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
        )

        request = RequestFactory().get("/")

        request.user = user

        tenant = TenantResolver.resolve(request)

        self.assertIsNotNone(tenant)

        self.assertEqual(
            tenant.organization_id,
            organization.id,
        )

        self.assertEqual(
            tenant.slug,
            organization.slug,
        )