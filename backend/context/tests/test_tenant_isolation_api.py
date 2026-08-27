from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
    Person,
)


User = get_user_model()


class ContextTenantIsolationAPITests(APITestCase):
    """
    Security regression tests for Context API tenant isolation.

    Verifies:
    - Own-tenant access works
    - Cross-tenant organization access is blocked
    - Cross-tenant BusinessObject access is blocked
    - Cross-tenant Person access is blocked
    - Authenticated users without organization membership are blocked
    - URL organization IDs cannot override authenticated membership
    """

    def setUp(self):

        # ---------------------------------------------------------
        # Tenant A
        # ---------------------------------------------------------

        self.organization_a = Organization.objects.create(
            name="Tenant A",
            slug="tenant-a",
        )

        self.user_a = User.objects.create_user(
            email="tenant-a@example.com",
            password="Password123",
        )

        OrganizationUser.objects.create(
            user=self.user_a,
            organization=self.organization_a,
            role="member",
        )

        # ---------------------------------------------------------
        # Tenant B
        # ---------------------------------------------------------

        self.organization_b = Organization.objects.create(
            name="Tenant B",
            slug="tenant-b",
        )

        self.user_b = User.objects.create_user(
            email="tenant-b@example.com",
            password="Password123",
        )

        OrganizationUser.objects.create(
            user=self.user_b,
            organization=self.organization_b,
            role="member",
        )

        # ---------------------------------------------------------
        # Shared object type
        # ---------------------------------------------------------

        self.object_type = BusinessObjectType.objects.create(
            name="Tenant Isolation Company",
            code="TENANT_ISOLATION_COMPANY",
        )

        # ---------------------------------------------------------
        # Business objects
        # ---------------------------------------------------------

        self.business_object_a = BusinessObject.objects.create(
            organization=self.organization_a,
            object_type=self.object_type,
            name="Tenant A Company",
            status="active",
        )

        self.business_object_b = BusinessObject.objects.create(
            organization=self.organization_b,
            object_type=self.object_type,
            name="Tenant B Company",
            status="active",
        )

        # ---------------------------------------------------------
        # People
        # ---------------------------------------------------------

        self.person_a = Person.objects.create(
            organization=self.organization_a,
            email="person-a@example.com",
            full_name="Person A",
        )

        self.person_b = Person.objects.create(
            organization=self.organization_b,
            email="person-b@example.com",
            full_name="Person B",
        )

        # Default authentication = Tenant A user
        self.client.force_authenticate(
            user=self.user_a,
        )

    # ============================================================
    # OWN TENANT ACCESS
    # ============================================================

    def test_user_can_access_own_organization360(self):

        response = self.client.get(
            f"/api/context/organization360/{self.organization_a.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_user_can_access_own_customer360(self):

        response = self.client.get(
            f"/api/context/customer360/{self.business_object_a.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_user_can_access_own_people360(self):

        response = self.client.get(
            f"/api/context/people360/{self.person_a.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ============================================================
    # ORGANIZATION-ID ISOLATION
    # ============================================================

    def test_organization360_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/organization360/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_communication_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/communication/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_executive_dashboard_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/executive-dashboard/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_search_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/search/{self.organization_b.id}/?q=test"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_ai_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/ai/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_risk_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/risk/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_opportunity_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/opportunity/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_workflow_blocks_cross_tenant_access(self):

        response = self.client.get(
            f"/api/context/workflow/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ============================================================
    # OBJECT-ID ISOLATION
    # ============================================================

    def test_customer360_blocks_cross_tenant_business_object(self):

        response = self.client.get(
            f"/api/context/customer360/{self.business_object_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_people360_blocks_cross_tenant_person(self):

        response = self.client.get(
            f"/api/context/people360/{self.person_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ============================================================
    # NO MEMBERSHIP
    # ============================================================

    def test_authenticated_user_without_membership_is_blocked(self):

        outsider = User.objects.create_user(
            email="outsider@example.com",
            password="Password123",
        )

        self.client.force_authenticate(
            user=outsider,
        )

        response = self.client.get(
            f"/api/context/organization360/{self.organization_a.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ============================================================
    # URL TENANT SWITCH ATTEMPT
    # ============================================================

    def test_url_organization_id_cannot_override_membership(self):

        self.assertNotEqual(
            self.organization_a.id,
            self.organization_b.id,
        )

        response = self.client.get(
            f"/api/context/organization360/{self.organization_b.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        own_response = self.client.get(
            f"/api/context/organization360/{self.organization_a.id}/"
        )

        self.assertEqual(
            own_response.status_code,
            status.HTTP_200_OK,
        )