from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from platform_core.context.security import (
    SecurityResolver,
)

User = get_user_model()


class SecurityContextTests(TestCase):

    def test_anonymous(self):

        request = RequestFactory().get("/")

        request.user = None

        security = SecurityResolver.resolve(
            request,
        )

        self.assertFalse(
            security.is_authenticated
        )

    def test_authenticated(self):

        user = User.objects.create_user(
            email="security@test.com",
            password="pass123",
        )

        request = RequestFactory().get("/")

        request.user = user

        security = SecurityResolver.resolve(
            request,
        )

        self.assertTrue(
            security.is_authenticated
        )

        self.assertEqual(
            security.email,
            user.email,
        )