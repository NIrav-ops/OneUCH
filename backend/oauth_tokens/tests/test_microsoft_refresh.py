from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from microsoftapis.utils import (
    refresh_microsoft_token,
)
from oauth_tokens.models import OAuthToken
from oauth_tokens.services import (
    get_valid_oauth_token,
)
from oauth_tokens.tasks import (
    refresh_expired_tokens,
)


User = get_user_model()


class MicrosoftRefreshTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="microsoft-refresh@oneuch.local",
            password="test-password-123",
        )

        self.token = OAuthToken.objects.create(
            user=self.user,
            provider="microsoft",
            access_token="expired-access-token",
            refresh_token="old-refresh-token",
            expires_at=timezone.now()
            - timedelta(minutes=5),
            is_active=True,
        )

    @patch(
        "microsoftapis.utils.requests.post"
    )
    def test_refresh_microsoft_token_updates_tokens(
        self,
        post,
    ):

        post.return_value.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }

        result = refresh_microsoft_token(
            self.token
        )

        self.token.refresh_from_db()

        self.assertEqual(
            result,
            "new-access-token",
        )

        self.assertEqual(
            self.token.access_token,
            "new-access-token",
        )

        self.assertEqual(
            self.token.refresh_token,
            "new-refresh-token",
        )

        self.assertTrue(
            self.token.is_active
        )

        self.assertGreater(
            self.token.expires_at,
            timezone.now(),
        )

    @patch(
        "microsoftapis.utils.requests.post"
    )
    def test_refresh_failure_disables_token(
        self,
        post,
    ):

        post.return_value.json.return_value = {
            "error": "invalid_grant",
        }

        with self.assertRaises(Exception):

            refresh_microsoft_token(
                self.token
            )

        self.token.refresh_from_db()

        self.assertFalse(
            self.token.is_active
        )

    @patch(
        "oauth_tokens.services."
        "refresh_microsoft_token"
    )
    def test_generic_service_refreshes_expired_microsoft_token(
        self,
        refresh,
    ):

        def perform_refresh(token):

            token.access_token = (
                "generic-new-access-token"
            )

            token.expires_at = (
                timezone.now()
                + timedelta(hours=1)
            )

            token.save(
                update_fields=[
                    "access_token",
                    "expires_at",
                ]
            )

            return token.access_token

        refresh.side_effect = perform_refresh

        token = get_valid_oauth_token(
            self.user,
            "microsoft",
        )

        refresh.assert_called_once_with(
            self.token
        )

        self.assertEqual(
            token.access_token,
            "generic-new-access-token",
        )

    @patch(
        "oauth_tokens.tasks."
        "refresh_microsoft_token"
    )
    def test_periodic_task_refreshes_expired_microsoft_token(
        self,
        refresh,
    ):

        refresh_expired_tokens()

        refresh.assert_called_once()

        refreshed_token = (
            refresh.call_args.args[0]
        )

        self.assertEqual(
            refreshed_token.id,
            self.token.id,
        )
