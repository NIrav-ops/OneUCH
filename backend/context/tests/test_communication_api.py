from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from inbox.models import Organization


class CommunicationIntelligenceAPITests(
    APITestCase,
):

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
            name="Test Org",
        )

    def test_status(self):

        response = self.client.get(
            f"/api/context/communication/{self.organization.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_contract(self):

        response = self.client.get(
            f"/api/context/communication/{self.organization.id}/"
        )

        expected = {

            "analytics",
            "channels",
            "trends",
            "response_times",
            "health",

        }

        self.assertEqual(
            set(response.data.keys()),
            expected,
        )

    def test_requires_authentication(self):

        self.client.logout()

        response = self.client.get(
            f"/api/context/communication/{self.organization.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_organization(self):

        response = self.client.get(
            "/api/context/communication/999999/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )