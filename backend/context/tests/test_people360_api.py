from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from context.models import Person

from inbox.models import Organization, OrganizationUser


class People360APITests(APITestCase):

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
            name="Test Organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.person = Person.objects.create(
            organization=self.organization,
            email="john@example.com",
            full_name="John Smith",
        )

    def test_status_code(self):

        response = self.client.get(
            f"/api/context/people360/{self.person.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_contract(self):

        response = self.client.get(
            f"/api/context/people360/{self.person.id}/"
        )

        expected = {

            "person",
            "timeline",
            "metrics",
            "health",

        }

        self.assertEqual(
            set(response.data.keys()),
            expected,
        )

    def test_requires_authentication(self):

        self.client.logout()

        response = self.client.get(
            f"/api/context/people360/{self.person.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_person(self):

        response = self.client.get(
            "/api/context/people360/999999/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )