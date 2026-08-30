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
    get_gmail_credentials,
    refresh_google_token as provider_google_refresh,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
    refresh_microsoft_token,
)

from oauth_tokens.models import (
    OAuthToken,
)

from oauth_tokens.services import (
    get_valid_oauth_token,
    refresh_google_token as canonical_google_refresh,
)


User = get_user_model()


class OAuthExecutionPolicyTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "oauth-policy@oneuch.test"
                ),
                password="pass123",
            )
        )

    def token(
        self,
        *,
        provider,
        disabled=False,
        expired=False,
    ):
        return OAuthToken.objects.create(
            user=self.user,
            provider=provider,
            access_token=(
                f"{provider}-access"
            ),
            refresh_token=(
                f"{provider}-refresh"
            ),
            expires_at=(
                timezone.now()
                - timedelta(minutes=5)
                if expired
                else
                timezone.now()
                + timedelta(hours=1)
            ),
            is_active=True,
            disabled_by_admin=disabled,
        )

    def test_canonical_service_blocks_admin_disabled_token(
        self,
    ):
        self.token(
            provider="google",
            disabled=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            get_valid_oauth_token(
                self.user,
                "google",
            )

    @patch(
        "oauth_tokens.services.requests.post"
    )
    def test_canonical_google_refresh_blocks_disabled_token_before_http(
        self,
        post,
    ):
        token = self.token(
            provider="google",
            disabled=True,
            expired=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            canonical_google_refresh(
                token
            )

        post.assert_not_called()

    @patch(
        "googleapis.utils.refresh_google_token"
    )
    def test_gmail_credentials_block_disabled_token_before_refresh(
        self,
        refresh,
    ):
        self.token(
            provider="google",
            disabled=True,
            expired=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            get_gmail_credentials(
                self.user
            )

        refresh.assert_not_called()

    @patch(
        "googleapis.utils.requests.post"
    )
    def test_provider_google_refresh_blocks_disabled_token_before_http(
        self,
        post,
    ):
        token = self.token(
            provider="google",
            disabled=True,
            expired=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            provider_google_refresh(
                token
            )

        post.assert_not_called()

    @patch(
        "microsoftapis.utils.refresh_microsoft_token"
    )
    def test_microsoft_access_blocks_disabled_token_before_refresh(
        self,
        refresh,
    ):
        self.token(
            provider="microsoft",
            disabled=True,
            expired=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            get_microsoft_access_token(
                self.user
            )

        refresh.assert_not_called()

    @patch(
        "microsoftapis.utils.requests.post"
    )
    def test_microsoft_refresh_blocks_disabled_token_before_http(
        self,
        post,
    ):
        token = self.token(
            provider="microsoft",
            disabled=True,
            expired=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            refresh_microsoft_token(
                token
            )

        post.assert_not_called()

    def test_active_provider_tokens_remain_usable(
        self,
    ):
        google_token = self.token(
            provider="google",
        )

        microsoft_token = self.token(
            provider="microsoft",
        )

        credentials = (
            get_gmail_credentials(
                self.user
            )
        )

        microsoft_access = (
            get_microsoft_access_token(
                self.user
            )
        )

        self.assertEqual(
            credentials.token,
            google_token.access_token,
        )

        self.assertEqual(
            microsoft_access,
            microsoft_token.access_token,
        )
