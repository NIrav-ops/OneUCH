from datetime import (
    timedelta,
)

from unittest.mock import (
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from googleapis.utils import (
    refresh_google_token as provider_google_refresh,
)

from oauth_tokens.models import (
    OAuthToken,
)

from oauth_tokens.services import (
    refresh_google_token as canonical_google_refresh,
)


User = get_user_model()


class GoogleRefreshFailureTruthTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "google-refresh-truth@oneuch.test"
                ),
                password="pass123",
            )
        )

    def create_token(
        self,
        *,
        refresh_token="google-refresh-token",
    ):
        return OAuthToken.objects.create(
            user=self.user,
            provider="google",
            access_token="expired-access-token",
            refresh_token=refresh_token,
            expires_at=(
                timezone.now()
                - timedelta(minutes=5)
            ),
            is_active=True,
        )

    @patch(
        "oauth_tokens.services.requests.post"
    )
    def test_canonical_provider_rejection_deactivates_token(
        self,
        post,
    ):
        token = self.create_token()

        post.return_value.json.return_value = {
            "error": "invalid_grant",
        }

        with self.assertRaises(Exception):
            canonical_google_refresh(
                token
            )

        token.refresh_from_db()

        self.assertFalse(
            token.is_active
        )

    @patch(
        "googleapis.utils.requests.post"
    )
    def test_runtime_provider_rejection_deactivates_token(
        self,
        post,
    ):
        token = self.create_token()

        post.return_value.json.return_value = {
            "error": "invalid_grant",
        }

        with self.assertRaises(Exception):
            provider_google_refresh(
                token
            )

        token.refresh_from_db()

        self.assertFalse(
            token.is_active
        )

    @patch(
        "oauth_tokens.services.requests.post"
    )
    def test_canonical_missing_refresh_token_requires_reauthentication(
        self,
        post,
    ):
        token = self.create_token(
            refresh_token=None,
        )

        with self.assertRaisesRegex(
            Exception,
            "refresh token missing",
        ):
            canonical_google_refresh(
                token
            )

        post.assert_not_called()

        token.refresh_from_db()

        self.assertFalse(
            token.is_active
        )

    @patch(
        "googleapis.utils.requests.post"
    )
    def test_runtime_missing_refresh_token_requires_reauthentication(
        self,
        post,
    ):
        token = self.create_token(
            refresh_token=None,
        )

        with self.assertRaisesRegex(
            Exception,
            "refresh token missing",
        ):
            provider_google_refresh(
                token
            )

        post.assert_not_called()

        token.refresh_from_db()

        self.assertFalse(
            token.is_active
        )

    @patch(
        "oauth_tokens.services.requests.post"
    )
    def test_transient_transport_failure_does_not_disconnect_token(
        self,
        post,
    ):
        token = self.create_token()

        post.side_effect = RuntimeError(
            "temporary network failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "temporary network failure",
        ):
            canonical_google_refresh(
                token
            )

        token.refresh_from_db()

        self.assertTrue(
            token.is_active
        )
