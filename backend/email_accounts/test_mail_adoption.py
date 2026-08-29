from datetime import (
    timedelta,
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

from rest_framework.test import (
    APIClient,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.adoption import (
    MailAdoptionService,
)

from inbox.models import (
    InboxSyncStatus,
    Organization,
    OrganizationUser,
)

from oauth_tokens.models import (
    OAuthToken,
)


User = get_user_model()


class MailAdoptionServiceTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-adoption@oneuch.test"
                ),
                password="pass123",
            )
        )

    def token(
        self,
        *,
        provider,
        expires_at=None,
        refresh_token="refresh-token",
        is_active=True,
        disabled_by_admin=False,
    ):
        return OAuthToken.objects.create(
            user=self.user,
            provider=provider,
            access_token="access-token",
            refresh_token=refresh_token,
            expires_at=(
                expires_at
                or (
                    timezone.now()
                    + timedelta(hours=1)
                )
            ),
            is_active=is_active,
            disabled_by_admin=(
                disabled_by_admin
            ),
        )

    def account(
        self,
        *,
        account_type,
        email,
        is_active=True,
    ):
        return EmailAccount.objects.create(
            user=self.user,
            account_type=account_type,
            email_address=email,
            is_active=is_active,
        )

    def provider(
        self,
        payload,
        provider,
    ):
        return next(
            item
            for item in payload[
                "providers"
            ]
            if (
                item[
                    "provider"
                ]
                == provider
            )
        )

    def test_disconnected_state_when_no_account_or_token(
        self,
    ):
        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        self.assertEqual(
            payload["summary"],
            {
                "supported": 2,
                "connected": 0,
                "disconnected": 2,
                "attention_required": 0,
                "synced_once": 0,
            },
        )

    def test_connected_gmail(
        self,
    ):
        account = self.account(
            account_type="gmail",
            email="user@gmail.com",
        )

        self.token(
            provider="google",
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "connection_status"
            ],
            "connected",
        )

        self.assertTrue(
            gmail["connected"]
        )

        self.assertEqual(
            gmail[
                "account_id"
            ],
            account.id,
        )

        self.assertEqual(
            gmail[
                "email_address"
            ],
            "user@gmail.com",
        )

    def test_connected_outlook(
        self,
    ):
        self.account(
            account_type="outlook",
            email="user@example.com",
        )

        self.token(
            provider="microsoft",
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        outlook = self.provider(
            payload,
            "microsoft",
        )

        self.assertEqual(
            outlook[
                "connection_status"
            ],
            "connected",
        )

    def test_expired_token_with_refresh_token_remains_connected(
        self,
    ):
        self.account(
            account_type="gmail",
            email="user@gmail.com",
        )

        self.token(
            provider="google",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
            refresh_token="refresh-token",
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "connection_status"
            ],
            "connected",
        )

        self.assertTrue(
            gmail[
                "token_expired"
            ]
        )

        self.assertTrue(
            gmail[
                "refresh_available"
            ]
        )

    def test_expired_token_without_refresh_requires_reauth(
        self,
    ):
        self.account(
            account_type="gmail",
            email="user@gmail.com",
        )

        self.token(
            provider="google",
            expires_at=(
                timezone.now()
                - timedelta(minutes=1)
            ),
            refresh_token=None,
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "connection_status"
            ],
            "reauth_required",
        )

        self.assertTrue(
            gmail[
                "attention_required"
            ]
        )

    def test_admin_disabled_token_is_reported(
        self,
    ):
        self.account(
            account_type="outlook",
            email="user@example.com",
        )

        self.token(
            provider="microsoft",
            disabled_by_admin=True,
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        outlook = self.provider(
            payload,
            "microsoft",
        )

        self.assertEqual(
            outlook[
                "connection_status"
            ],
            "admin_disabled",
        )

        self.assertTrue(
            outlook[
                "attention_required"
            ]
        )

    def test_inactive_email_account_requires_reauth(
        self,
    ):
        self.account(
            account_type="gmail",
            email="user@gmail.com",
            is_active=False,
        )

        self.token(
            provider="google",
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "connection_status"
            ],
            "reauth_required",
        )

    def test_sync_status_is_projected(
        self,
    ):
        self.account(
            account_type="gmail",
            email="user@gmail.com",
        )

        self.token(
            provider="google",
        )

        sync = InboxSyncStatus.objects.create(
            user=self.user,
            platform="gmail",
            status="success",
            progress=100,
            last_synced_at=timezone.now(),
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "sync_status"
            ],
            "success",
        )

        self.assertEqual(
            gmail[
                "sync_progress"
            ],
            100,
        )

        self.assertEqual(
            gmail[
                "last_synced_at"
            ],
            sync.last_synced_at,
        )

        self.assertEqual(
            payload[
                "summary"
            ][
                "synced_once"
            ],
            1,
        )

    def test_other_users_mailbox_is_not_included(
        self,
    ):
        other = (
            User.objects.create_user(
                email=(
                    "other-mail@oneuch.test"
                ),
                password="pass123",
            )
        )

        EmailAccount.objects.create(
            user=other,
            account_type="gmail",
            email_address="other@gmail.com",
            is_active=True,
        )

        OAuthToken.objects.create(
            user=other,
            provider="google",
            access_token="other-token",
            refresh_token="other-refresh",
            expires_at=(
                timezone.now()
                + timedelta(hours=1)
            ),
            is_active=True,
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user
            )
        )

        gmail = self.provider(
            payload,
            "google",
        )

        self.assertEqual(
            gmail[
                "connection_status"
            ],
            "disconnected",
        )


class MailAdoptionAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "mail-adoption-api@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Mail Adoption Org"
                ),
                slug=(
                    "mail-adoption-org"
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

    def test_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_api_requires_membership(
        self,
    ):
        outsider = (
            User.objects.create_user(
                email=(
                    "mail-outsider@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_inactive_organization(
        self,
    ):
        self.organization.is_active = False

        self.organization.save(
            update_fields=[
                "is_active"
            ]
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_returns_supported_providers(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "summary"
            ][
                "supported"
            ],
            2,
        )

        self.assertEqual(
            {
                item[
                    "provider"
                ]
                for item in response.data[
                    "providers"
                ]
            },
            {
                "google",
                "microsoft",
            },
        )
