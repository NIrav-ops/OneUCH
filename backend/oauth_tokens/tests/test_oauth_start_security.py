from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inbox.models import (
    Organization,
    OrganizationUser,
)


class OAuthStartSecurityTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="oauth-test@oneuch.local",
            password="test-password-123",
        )

        self.organization = (
            Organization.objects.create(
                name="OAuth Test Workspace",
                slug=(
                    "oauth-test-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

        self.client = APIClient()

    def test_google_start_requires_authentication(self):
        response = self.client.get(
            "/api/google/oauth/start/"
        )

        self.assertIn(
            response.status_code,
            {401, 403},
        )

    def test_microsoft_start_requires_authentication(self):
        response = self.client.get(
            "/api/microsoft/oauth/start/"
        )

        self.assertIn(
            response.status_code,
            {401, 403},
        )

    def test_google_start_returns_authorization_url_for_authenticated_user(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/google/oauth/start/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertIn(
            "authorization_url",
            payload,
        )

        self.assertIn(
            "accounts.google.com",
            payload["authorization_url"],
        )

        self.assertIn(
            "state=",
            payload["authorization_url"],
        )

    def test_microsoft_start_returns_authorization_url_for_authenticated_user(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/microsoft/oauth/start/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "authorization_url",
            response.data,
        )

        self.assertIn(
            "login.microsoftonline.com",
            response.data[
                "authorization_url"
            ],
        )

        self.assertIn(
            "Mail.Send",
            response.data[
                "authorization_url"
            ],
        )

        self.assertIn(
            "state=",
            response.data[
                "authorization_url"
            ],
        )