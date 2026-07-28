from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from platform_core.api.permissions import (
    EnterprisePermission,
    AdminPermission,
    ReadOnlyPermission,
)


class APIFoundationTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(

            email="user@test.com",

            password="Password123",

        )

        self.admin = User.objects.create_superuser(

            email="admin@test.com",

            password="Password123",

        )

        self.factory = APIRequestFactory()


    def test_enterprise_permission(self):

        request = self.factory.get("/")

        request.user = self.user

        self.assertTrue(

            EnterprisePermission().has_permission(

                request,

                None,

            )

        )


    def test_admin_permission(self):

        request = self.factory.get("/")

        request.user = self.admin

        self.assertTrue(

            AdminPermission().has_permission(

                request,

                None,

            )

        )


    def test_read_only_permission(self):

        request = self.factory.get("/")

        self.assertTrue(

            ReadOnlyPermission().has_permission(

                request,

                None,

            )

        )


    def test_post_not_allowed(self):

        request = self.factory.post("/")

        self.assertFalse(

            ReadOnlyPermission().has_permission(

                request,

                None,

            )

        )