from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from inbox.models import Organization, OrganizationUser


class WorkflowIntelligenceAPITests(APITestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        self.organization = Organization.objects.create(
            name="Workflow Test Organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

    def test_status_code(self):

        response = self.client.get(
            f"/api/context/workflow/{self.organization.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_contract(self):

        response = self.client.get(
            f"/api/context/workflow/{self.organization.id}/"
        )

        self.assertIn(
            "dashboard",
            response.data,
        )

    def test_requires_authentication(self):

        self.client.logout()

        response = self.client.get(
            f"/api/context/workflow/{self.organization.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_organization(self):

        response = self.client.get(
            "/api/context/workflow/999999/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )