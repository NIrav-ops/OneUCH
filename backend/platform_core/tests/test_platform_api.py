from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class PlatformAPITests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(

            email="admin@test.com",

            password="Password123",

        )

        self.client = APIClient()

        self.client.force_authenticate(

            self.user,

        )

    def test_health(self):

        response = self.client.get(

            "/api/platform/health/",

        )

        self.assertEqual(

            response.status_code,

            200,

        )

    def test_metrics(self):

        response = self.client.get(

            "/api/platform/metrics/",

        )

        self.assertEqual(

            response.status_code,

            200,

        )

    def test_configuration(self):

        response = self.client.get(

            "/api/platform/configuration/",

        )

        self.assertEqual(

            response.status_code,

            200,

        )

    def test_jobs(self):

        response = self.client.get(

            "/api/platform/jobs/",

        )

        self.assertEqual(

            response.status_code,

            200,

        )

    def test_scheduler(self):

        response = self.client.get(

            "/api/platform/scheduler/",

        )

        self.assertEqual(

            response.status_code,

            200,

        )